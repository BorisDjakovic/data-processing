from md_covid19cases import credentials
import common
import os
import pandas as pd

print(f'Reading data into dataframe...')
filename = os.path.join(credentials.path, credentials.filename_faelle)
df = pd.read_csv(filename, sep=';')
print(f'Keeping only certain columns...')

df = df[['datum', 'faelle_bs_kum', 'faelle_bs', 'faelle_basel', 'faelle_basel_kum', 'faelle_riehen',
         'faelle_riehen_kum', 'faelle_bettingen', 'faelle_bettingen_kum', 'inzidenz07_bs', 'inzidenz14_bs',
         'summe_07_tage_bs', 'summe_14_tage_bs', 'mittel_07_tage_bs', 'mittel_14_tage_bs',
         # The following columns will be published as soon as they're ready:
         # 'inzidenz_riehen_07', 'inzidenz_riehen_14',
         # 'inzidenz_bettingen_07', 'inzidenz_bettingen_14',
         # 'inzidenz_basel_07', 'inzidenz_basel_14'
         ]]

export_filename = os.path.join(credentials.export_path, credentials.export_filename_faelle)
print(f'Exporting csv to {export_filename}')
df.to_csv(export_filename, index=False)

common.upload_ftp(export_filename, credentials.ftp_server, credentials.ftp_user, credentials.ftp_pass, 'md/covid19_cases')
print('Job successful!')
