import logging
import pandas as pd
import numpy as np
import geopandas as gpd
from datetime import datetime, timedelta
import os
import common
from stadtreinigung_wildedeponien import credentials
from io import StringIO
import common.change_tracking as ct
import ods_publish.etl_id as odsp


def get_text_from_url(url):
    req = common.requests_get(url)
    req.raise_for_status()
    return req.text

def randomize_coordinates(row):
    shift_size = 25
    random_seed = hash((row['lat'], row['lon'], credentials.hash_salt)) % (2**32 - 1)
    np.random.seed(random_seed)
    displacement = np.random.uniform(-shift_size, shift_size, size=2)
    row['randomly_shifted_lat'] = row['lat'] + displacement[0]
    row['randomly_shifted_lon'] = row['lon'] + displacement[1]
    return row


def main():
    # Get only data since yesterday
    # from_timestamp = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    # api_url = f'https://tba-bs.ch/export?object=sr_wilde_deponien_v2_ogd&from=2010-01-01&format=csv'

    # get all data once
    api_url = f'https://tba-bs.ch/export?object=sr_wilde_deponien_v2_ogd&format=csv'

    logging.info(f'Retrieving data from API call to "{api_url}"...')
    r = common.requests_get(url=api_url, auth=(credentials.api_user, credentials.api_password))
    if len(r.text) == 0:
        logging.error('No data retrieved from API!')
        raise RuntimeError('No data retrieved from API.')
    else:
        data = StringIO(r.text)
        df = pd.read_csv(data, sep=';')
        logging.info('Retrieving lat and lon from column "geometry"...')
        df['coords'] = df.geometry.str.replace('POINT(', '', regex=False)
        df['coords'] = df.coords.str.replace(')', '', regex=False)
        # df['coords'] = df.coords.str.replace(' ', ',', regex=False)
        df2 = df['coords'].str.split(' ', expand=True)
        df = df.assign(lon=df2[[0]], lat=df2[[1]])
        df.lat = pd.to_numeric(df.lat)
        df.lon = pd.to_numeric(df.lon)

        logging.info("Randomizing coordinates and getting rid of data we don't want to have published...")
        df = df.apply(randomize_coordinates, axis=1)

        df.drop(['geometry', 'coords', 'lat', 'lon', 'adresse'], axis=1, inplace=True)

        # logging.info('Extracting lat and long using regex from column "koordinaten..."')
        # 'POINT\((?<long> \d *.\d *)\s(?<lat> \d *.\d *)\)'

        logging.info('Creating ISO8601 timestamps with timezone info...')
        df['Timestamp'] = pd.to_datetime(df['meldung_erfassungszeit'])
        # df['Timestamp'] = pd.to_datetime(df['bearbeitungszeit_meldung'], format='%Y-%m-%d %H:%M:%S%Z')
        # df['Timestamp'] = df['Timestamp'].dt.tz_localize('Europe/Zurich')
        df['bearbeitungszeit_meldung'] = df['Timestamp']
        df.drop(['Timestamp'], axis=1, inplace=True)

        logging.info('Reading Bezirk data into geopandas df...')
        # see e.g. https://stackoverflow.com/a/58518583/5005585
        get_text_from_url('https://data.bs.ch/explore/dataset/100042/download/?format=geojson')

        df_wv = gpd.read_file(get_text_from_url('https://data.bs.ch/explore/dataset/100042/download/?format=geojson'))
        df_bez = gpd.read_file(get_text_from_url('https://data.bs.ch/explore/dataset/100039/download/?format=geojson'))
        df_points = gpd.GeoDataFrame(df, crs="EPSG:2056", geometry=gpd.points_from_xy(df.randomly_shifted_lon, df.randomly_shifted_lat))
        logging.info('Re-projecting points...')
        df_points = df_points.to_crs('EPSG:4326')
        logging.info('Spatially joining points with Wohnviertel...')
        gdf_wv = gpd.sjoin(df_points, df_wv, how='left', op="within", rsuffix='wv', lsuffix='points')
        logging.info('Spatially joining points with Bezirk...')
        gdf_wv_bez = gpd.sjoin(gdf_wv, df_bez, how='left', op="within", rsuffix='bez', lsuffix='points')
        logging.info('Dropping unnecessary columns...')
        gdf_wv_bez.drop(columns=['index_wv', 'index_bez', 'wov_id_points', 'meldung_erfassungszeit', 'geometry'], inplace=True)

        # todo: Find nearest Wohnviertel / Bezirk of points outside of those shapes (Rhein, Outside of BS territory)
        # e.g. see https://gis.stackexchange.com/a/342489

        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        file_path = os.path.join(credentials.path, f'{credentials.filename_with_rand_loc}')
        logging.info(f'Exporting data to {file_path}...')
        gdf_wv_bez.to_csv(file_path, index=False, date_format='%Y-%m-%dT%H:%M:%S%z')

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.info(f'Executing {__file__}...')
    main()
    logging.info('Job successful!')
