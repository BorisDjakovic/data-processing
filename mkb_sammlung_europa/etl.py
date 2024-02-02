import pandas as pd
from mkb_sammlung_europa import credentials
import common
import logging
from common import change_tracking as ct
import ods_publish.etl_id as odsp


def main():
    path = credentials.path_data
    df_MKB = common.pandas_read_csv(path, encoding='utf8')
    df_MKB = remove_commas_at_end(df_MKB)
    df_MKB = remove_irrelevant(df_MKB)
    # split up Kurzbezeichning and Titel
    df_MKB[['Kurzbezeichnung', 'Titel']] = df_MKB['Kurzbezeichnung und Titel'].str.split(':', expand=True, n=1)
    # split off Einlaufnummer from Einlauf-Info
    df_MKB[['Einlaufnummer', 'Einlauf-Info']] = df_MKB['Einlauf-Info'].str.split(',', expand=True, n=1)
    # "Aus rechtlichen Gründen nicht angezeigt" should appear in both columns
    df_MKB['Einlauf-Info'].fillna('Aus rechtlichen Gründen nicht angezeigt', inplace=True)
    # remove Einlaufnummern VI_0000.1, VI_0000.2
    df_MKB = remove_einlaufnummern(df_MKB)
    # Select columns in the right order
    df_MKB = df_MKB[["Inventarnummer", "Einlaufnummer", "Kurzbezeichnung", "Titel", "Datierung",
                     "Material & Technik", "Masse", "Herkunft", "Einlauf-Info"]]
    # join duplicates
    df_MKB = join_duplicates(df_MKB)
    # df_MKB.to_csv("MKB_Sammlung_Europa_new.csv", index=False)
    # export new file
    df_MKB.to_csv(credentials.path_export_file, index=False)
    if ct.has_changed(credentials.path_export_file):
        common.upload_ftp(credentials.path_export_file, credentials.ftp_server, credentials.ftp_user,
                          credentials.ftp_pass, 'mkb/sammlung_europa')
        odsp.publish_ods_dataset_by_id('100148')
        ct.update_hash_file(credentials.path_export_file)
    logging.info('Job successful!')


def remove_commas_at_end(df):
    for column in list(df.columns):
        df[column] = df[column].str.rstrip(', ')
    return df


def find_missing_values(df):
    for column in list(df.columns):
        missing = pd.isnull(df[column]).sum()
        print("there are " + str(missing) + " missing in the column " + column)


# remove Einlaufnummern VI_0000.1, VI_0000.2
def remove_einlaufnummern(df):
    df1 = df[df["Einlaufnummer"] == 'VI_0000.1']
    df2 = df[df["Einlaufnummer"] == 'VI_0000.2']
    df_without_df1 = df.drop(df1.index)
    df_without_df1_df2 = df_without_df1.drop(df2.index)
    return df_without_df1_df2


# extract irrelevant text in Datierung using Hackathon file
def remove_irrelevant(df_MKB):
    path = credentials.path_hackathon
    df_new = common.pandas_read_csv(path)
    text_to_remove = list(df_new["Datierung_Info"].unique())

    # after inspection remove some items from list that should stay
    text_to_remove.remove("189")
    text_to_remove.remove("19")
    text_to_remove.remove("198")
    text_to_remove.remove("30er, ev. sogar 20er Jahre")
    text_to_remove.remove("bis 1850 verwendet")
    text_to_remove.remove("Wende 17. Jh.")
    text_to_remove.remove("Mitte 1930")
    text_to_remove.remove("300 v. Chr.")
    text_to_remove.remove("I")

    # add some different spellings I noticed
    text_to_remove = text_to_remove + ["Jüdisch", "Judentum", "Biedermeier (Imitation?)"]

    # add different formats: kommas, white space, upper case, brackets..
    text_to_remove_appended = []
    for item in text_to_remove:
        item = str(item)
        text_to_remove_appended = text_to_remove_appended + [item.upper(), item.lower()]
    text_to_remove = text_to_remove_appended + text_to_remove
    text_to_remove_appended = []
    for item in text_to_remove:
        item = str(item)
        text_to_remove_appended = text_to_remove_appended + ["," + item, item + ",", "("+item+")"]
    text_to_remove = text_to_remove_appended + text_to_remove
    text_to_remove_with_white_space = []
    for item in text_to_remove:
        item = str(item)
        text_to_remove_with_white_space = text_to_remove_with_white_space + [" " + item + " ", " " + item, item + " "]
    text_to_remove = text_to_remove + text_to_remove_with_white_space

    # add some more items that were not removed on first try
    text_to_remove = ["Antike (altrömisch),", "Deutschland (Westdeutschland),", "Ruthenen (Lemken)"] + text_to_remove + ["(Lemken),", "(alt),", "/ Araber,", "(West),", "(?),"]

    # remove text from Datierung column
    for item in text_to_remove:
        df_MKB["Datierung"] = df_MKB["Datierung"].str.replace(str(item), "", regex=False)
    return df_MKB



def join_duplicates(df_MKB):
    # make Herkunft string
    # df_MKB['Herkunft'] = df_MKB['Herkunft'].to_string()
    # first make sure dataset is sorted by Inventarnummer
    df_MKB = df_MKB.sort_values(by=["Inventarnummer"])
    duplicates = df_MKB.duplicated(subset=["Inventarnummer"], keep=False)
    index_duplicates = df_MKB[duplicates].index

    # note: 96 rows with double Inventarnummer, for all checked this is caused by different entries for "Herkunft"
    # check if it is always caused by different entry for "Herkunft" (it is):
    # columns = list(df_MKB.columns)
    # columns.remove('Herkunft')
    # duplicates_without_herkunft = df_MKB.duplicated(subset=columns, keep=False)
    # print(df_MKB[duplicates_without_herkunft])

    # first remove all duplicates
    df_MKB_without_duplicates = df_MKB.drop(index_duplicates)
    # split duplicates into two dataframes
    list_inventar_duplicates_1 = df_MKB[df_MKB.duplicated(subset=["Inventarnummer"], keep='first')].reset_index()
    list_inventar_duplicates_2 = df_MKB[df_MKB.duplicated(subset=["Inventarnummer"], keep='last')].reset_index()
    # make dataframe with one entry for each duplicate, with two different entries for Herkunft separated by a comma
    df_duplicates = list_inventar_duplicates_1[["Inventarnummer", "Einlaufnummer", "Kurzbezeichnung", "Titel", "Datierung",
                     "Material & Technik", "Masse", "Einlauf-Info"]]
    df_duplicates['Herkunft']=''
    df_duplicates["Herkunft"] = list_inventar_duplicates_1['Herkunft'].astype(str) + ", " + list_inventar_duplicates_2['Herkunft'].astype(str)
    # concatenate the two data frames
    df_MKB = pd.concat([df_MKB_without_duplicates, df_duplicates])
    return df_MKB


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.info(f'Executing {__file__}...')
    main()
