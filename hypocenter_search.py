#! /usr.bin/env python3

from datetime import timedelta

import pandas as pd
import requests
from bs4 import BeautifulSoup
from obspy.core import UTCDateTime


def _dict_bibli_search(searcher, args):
    """
    arg -> search parameters
    """
    #
    if args.date is None:
        searcher.start_date = args.start_date
        searcher.end_date = args.end_date
    else:
        searcher.start_date = args.date
        searcher.end_date = searcher.start_date + timedelta(days=1)
    if args.reviewed:
        searcher.reviewed = "REVIEWED"
    else:
        searcher.reviewed = "COMPREHENSIVE"
    # TODO: Setup saerch region
    if args.shape is not None:
        searcher.shape = args.shape
        searcher.coords = args.coords
    else:
        searcher.shape = "POLY"
        searcher.coords = ""
    # TODO dep, mag, and phase filters

    searcher.optional_outputs = ""
    if args.include_null_mag:
        searcher.optional_outputs += "&null_mag=on"
    if args.include_null_phs:
        searcher.optional_outputs += "&null_phs=on" 
    if args.only_prime_hypo:
        searcher.optional_outputs += "&prime_only=on"  
    if args.include_phases:
        searcher.optional_outputs += "&include_phases=on"  
    if args.include_magnitudes:
        searcher.optional_outputs += "&include_magnitudes=on"  
    if args.include_weblinks:
        searcher.optional_outputs += "&include_links=on"  
    if args.include_headers:
        searcher.optional_outputs += "&include_headers=on" 
    if args.include_comments:
        searcher.optional_outputs += "&include_comments=on"

    searcher.source = "ISC Bulletin"


def format_url(searcher, args):
    """
    searcher -> url
    """
    # Extract search params
    _dict_bibli_search(searcher, args)
    # Format URL
    base = "http://isc-mirror.iris.washington.edu/cgi-bin/web-db-run"
    request = f"?request={searcher.reviewed}"
    output_format = "&out_format=QuakeML"
    # TODO: setup saerch region
    shape = "&searchshape=RECT"
    rect_search = "&bot_lat=&top_lat=&left_lon=&right_lon="
    circ_search = "&ctr_lat=&ctr_lon=&radius=&max_dist_units=deg"
    seismic_region = "&srn="
    geographic_region = "&grn="
    start_year = f"&start_year={searcher.start_date.year}"
    start_month = "f&start_month={searcher.start_date.month}"
    start_day = f"&start_day={searcher.start_date.day}"
    start_time = "&start_time=00%3A00%3A00"
    end_year = f"&end_year={searcher.end_date.year}"
    end_month = f"&end_month={searcher.end_date.month}"
    end_day = f"&end_day={searcher.end_date.day}"
    end_time = "&end_time=00%3A00%3A00"
    # TODO dep, mag, and phase filters
    min_dep = "&min_dep="
    max_dep = "&max_dep="
    min_mag = "&min_mag="
    max_mag = "&max_mag="
    mag_type = "&req_mag_type="
    mag_agency = "&req_mag_agcy="
    min_defining_phase = "&min_def="
    max_defining_phase = "&max_def="
    optional_outputs = searcher.optional_outputs

    url = (
        base
        + request
        + output_format
        + shape
        + rect_search
        + circ_search
        + seismic_region
        + geographic_region
        + start_year
        + start_month
        + start_day
        + start_time
        + end_year
        + end_month
        + end_day
        + end_time
        + min_dep
        + max_dep
        + min_mag
        + max_mag
        + mag_type
        + mag_agency
        + min_defining_phase
        + max_defining_phase
        + optional_outputs
    )

    return url


def fetch_url(url):
    """
    fetch html and parse out body text
    """
    print("Search URL:\n", url)
    # reqest web page
    response = requests.get(url)
    # get HTML text
    html = response.text
    # parse the HTML
    soup = BeautifulSoup(html, "html.parser")
    # isolate body text
    body = soup.body

    return body


def parse_bibli_page(searcher, body):
    """
    parse catalog from html body text
    """
    lines = [line for line in body.strings]
    # TODO: integrate RegularExpressions
    # Check empty search
    if "No events with references were found" in lines[23]:
        print()
        print(lines[23])
        exit()
    # TODO:split search catalog
    if "limited to 500 seismic events" in lines[23]:
        print()
        print(lines[23])
        exit()
    # Parse content
    header_pos = [n for n, line in enumerate(lines) if line[:4] == " ISC"]
    header_pos.append(len(lines))
    # init catalog
    header_info = [
        "origin_time",
        "lat",
        "lon",
        "dep",
        "mag_type",
        "mag",
        "mag_reporting_agency",
        "event_reporting_agency",
        "event_code",
        "article_num",
        "articles",
    ]
    rows = []
    for n, pos in enumerate(header_pos[:-1]):
        # Split headers and event info
        headers = lines[pos].split()
        event_info = lines[pos + 2].split()
        # Parse

        event_reporting_agency = event_info[0]
        origin_time = UTCDateTime(event_info[1] + "T" + event_info[2])
        lat = event_info[3]
        lon = event_info[4]
        dep = event_info[5]
        if len(event_info) < 10:
            num_articles = int(event_info[6])
            mag_type = ""
            mag_reporting_agency = ""
            mag = ""
        else:
            # TODO: sep mag type and mag source
            mag_type = event_info[6].split("(")[0]
            mag_reporting_agency = event_info[6].split("(")[0]
            mag = event_info[8]
            # Parse numhber of articles
            num_articles = int(event_info[9])
        # Check for event_code
        if "code" in headers:
            event_code = event_info[-1]
        else:
            event_code = ""
        # Iterate through articles
        article_lines = "".join(lines[pos + 3 : header_pos[n + 1]]).split("\n")
        for m in range(num_articles):
            row = [
                origin_time,
                lat,
                lon,
                dep,
                mag_type,
                mag,
                mag_reporting_agency,
                event_reporting_agency,
                event_code,
                m + 1,
                article_lines[m],
            ]
            rows.append(row)
    catalog = pd.DataFrame(rows, columns=header_info)
    searcher.earthquake_catalog = catalog
