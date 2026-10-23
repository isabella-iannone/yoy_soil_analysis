# getting the SSURGO data from the website


import requests
import pandas as pd
import geopandas as gpd
from requests.adapters import HTTPAdapter
from shapely import wkt as shapely_wkt
from urllib3.util.retry import Retry

SDA = "https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest"
TIMEOUT = 120
MUKEY_CHUNK = 500 
ALBERS = 5070
WGS84 = 4326

HORIZON_NUMERIC = ["comppct_r", "hzdept_r", "hzdepb_r", "om_r", "dbthirdbar_r"]


class SDAError(RuntimeError):
    """There is an error in the results table from pulling SDA information"""


def _session():
    retry = Retry(total=3, backoff_factor=2, status_forcelist=[500, 502, 503, 504],
                  allowed_methods=["POST"])
    s = requests.Session()
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s

def sda_query(query):
    """Run one SQL query against SDA and return a DataFrame of strings."""
    try:
        r = _session().post(SDA, json={"query": query, "format": "JSON+COLUMNNAME"},
                            timeout=TIMEOUT)
    except requests.RequestException as e:
        raise SDAError(f"Could not reach Soil Data Access: {e}") from e
 
    if r.status_code != 200:
        raise SDAError(f"SDA returned {r.status_code}: {r.text[:500]}")
 
    body = r.json() if r.text.strip() else {}
    rows = body.get("Table")
    if not rows:  # SDA sends back an empty object when a query matches nothing
        return pd.DataFrame()
    return pd.DataFrame(rows[1:], columns=rows[0])
 
 
def _check_wkt(farm_wkt):
    # Fails early with a clear message instead of an SDA SQL error
    try:
        shapely_wkt.loads(farm_wkt)
    except Exception as e:
        raise ValueError(f"farm_wkt is not valid WKT: {e}") from e
 
 
def _clean_mukeys(mukeys):
    # mukeys are numeric strings; anything else would break or alter the SQL
    keys = sorted({str(k).strip() for k in mukeys if pd.notna(k)})
    bad = [k for k in keys if not k.isdigit()]
    if bad:
        raise ValueError(f"Invalid mukey values: {bad[:5]}")
    return keys
 
 
def get_polygons(farm_wkt):
    """SSURGO map unit polygons that intersect the farm boundary, cut to it.
 
    farm_wkt: boundary in WGS84 (EPSG:4326), e.g. from
              ssurgo_carbon.farm_boundary_wkt(fields_gdf).
    Returns a GeoDataFrame with mukey, musym, muname, geometry.
    """
    _check_wkt(farm_wkt)
    aoi = f"geometry::STGeomFromText('{farm_wkt}', 4326)"
    query = f"""
        SELECT p.mukey, p.musym, mu.muname,
               p.mupolygongeo.STIntersection({aoi}).STAsText() AS geom_wkt
        FROM mupolygon AS p
        JOIN mapunit AS mu ON mu.mukey = p.mukey
        WHERE p.mupolygongeo.STIntersects({aoi}) = 1
    """
    df = sda_query(query)
    if df.empty:
        return gpd.GeoDataFrame(columns=["mukey", "musym", "muname", "geometry"],
                                geometry="geometry", crs=4326)
    geoms = gpd.GeoSeries.from_wkt(df["geom_wkt"], crs=4326)
    return gpd.GeoDataFrame(df.drop(columns="geom_wkt"), geometry=geoms)
 
 
def get_horizons(mukeys):
    """Component and horizon properties for the given map units.
 
    One row per horizon of each component. Returned unfiltered:
    choosing depths, components and missing values is ssurgo_carbon's job.
    """
    keys = _clean_mukeys(mukeys)
    if not keys:
        return pd.DataFrame()
 
    chunks = []
    for start in range(0, len(keys), MUKEY_CHUNK):
        in_list = ",".join(f"'{k}'" for k in keys[start:start + MUKEY_CHUNK])
        chunks.append(sda_query(f"""
            SELECT c.mukey, c.cokey, c.compname, c.comppct_r, c.majcompflag,
                   h.chkey, h.hzname, h.hzdept_r, h.hzdepb_r, h.om_r, h.dbthirdbar_r
            FROM component AS c
            JOIN chorizon AS h ON h.cokey = c.cokey
            WHERE c.mukey IN ({in_list})
        """))
 
    df = pd.concat(chunks, ignore_index=True)
    if df.empty:
        return df
    # SDA returns every value as text; blanks become NaN
    for col in HORIZON_NUMERIC:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def farm_boundary_wkt(fields_gdf, buffer_m=20, tolerance_deg=0.0001):
    """One merged, slightly padded farm boundary as WKT in WGS84, for SDA queries."""
    shape = fields_gdf.to_crs(ALBERS).union_all().buffer(buffer_m)
    boundary = gpd.GeoSeries([shape], crs=ALBERS).to_crs(WGS84)
    return boundary.simplify(tolerance_deg).iloc[0].wkt