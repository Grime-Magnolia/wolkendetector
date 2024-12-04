#!/bin/python
import requests
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import argparse
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def fetch_and_process_data(url, debug=False):
    response = requests.get(url)
    if debug:
        print(f"Status code: {response.status_code}")
        print(f"Response preview: {response.text[:200]}")
    nonstriped_lines = lines = [x for x in response.text.split("\n")]
    lines = [x for x in response.text.split("\n") if "#" not in x and x]
    data = []
    time_data = []
    highest = (0, -1)
    start_night = end_night = 0
    name = nonstriped_lines[5].split('_')[-1]
    print(name)
    for i, line in enumerate(lines):
        parts = line.split(';')
        entry = {
            "local-timestamp": parts[1],
            "Temperature": float(parts[2]),
            "Frequency": float(parts[4]),
            "MSAS": float(parts[5])
        }
        time_data.append(datetime.datetime.strptime(entry["local-timestamp"], "%Y-%m-%dT%H:%M:%S.%f"))
        data.append(entry)
        
        if start_night == 0 and entry["MSAS"] != 0:
            start_night = i
        if entry["MSAS"] > highest[0]:
            highest = (entry["MSAS"], i)

    for i in range(len(data) - 1, 0, -1):
        if data[i]["MSAS"] != 0:
            end_night = i
            break

    return data, time_data, highest, start_night, end_night

def fetch_and_process_site(url, debug=False):
    base_url = "https://www.washetdonker.nl/data/"
    
    if not urlparse(url).scheme:
        url = urljoin(base_url, url)
    
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    dir_list = soup.find(id='directory-listing')
    year_url = base_url + dir_list.contents[3].find('a')['href']
    
    response = requests.get(year_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    dir_list = soup.find(id='directory-listing')
    month_url = base_url + dir_list.contents[3].find('a')['href']
    
    response = requests.get(month_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    day_url = soup.find(id="directory-listing").contents[3]["data-href"]
    
    if debug:
        print(f"Year URL: {year_url}")
        print(f"Month URL: {month_url}")
        print(f"Day URL: {base_url + day_url}")
        
    return fetch_and_process_data(base_url + day_url, debug=debug)

def calculate_averages(data, start_night, end_night, modifier=1.25):
    night_data = [d["MSAS"] for d in data[start_night:end_night+1]]
    average = sum(night_data) / len(night_data)
    average_offset = sum(abs(x - average) for x in night_data) / len(night_data) / modifier
    return average, average_offset

def find_night_indices(data, average, average_offset, start_night, end_night):
    threshold = average - average_offset
    min_night_index = next(i for i in range(start_night, end_night+1) if data[i]["MSAS"] > threshold)
    max_night_index = next(i for i in range(end_night, start_night-1, -1) if data[i]["MSAS"] > threshold)
    return min_night_index, max_night_index

def plot_data(data, time_data, average, average_offset, start_night, end_night, min_night_index, max_night_index, debug=False):
    fig, ax = plt.subplots(figsize=(12, 6))
    ys = [d["MSAS"] for d in data]
    topline = average_offset * 1.1 + average

    ax.plot(time_data, ys, label="MSAS Over Time")

    night_index_time = time_data[min_night_index:max_night_index+1]
    y_night_index = ys[min_night_index:max_night_index+1]
    tja = np.full_like(y_night_index, topline)
    where_condition = np.greater(tja, y_night_index)
    ax.fill_between(night_index_time, y_night_index, tja, where=where_condition, interpolate=True, color="green", alpha=0.5)

    ax.axhline(y=topline, color='b', linestyle='dotted', label="Average positive offset of the average MSAS")
    ax.axhline(y=average - average_offset, color='b', linestyle='dotted', label="Average negative offset of the average MSAS")
    ax.axvline(x=night_index_time[0], color='r', linestyle='dotted')
    ax.axvline(x=night_index_time[-1], color='r', linestyle='dotted')    
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    fig.autofmt_xdate()

    ax.set_xlabel('Local Time')
    ax.set_ylabel('MSAS')
    ax.set_title('MSAS Over Time')
    plt.legend()
    plt.show()

def main(url="https://www.washetdonker.nl/data/Noordpolderzijl/2024/09/20240930_120000_SQM-Noordpolderzijl.dat", debug=False):        
    if ".dat" in url:
        data, time_data, highest, start_night, end_night = fetch_and_process_data(url, debug=debug)
    else:
        data, time_data, highest, start_night, end_night = fetch_and_process_site(url, debug=debug)
    
    average, average_offset = calculate_averages(data, start_night, end_night)
    min_night_index, max_night_index = find_night_indices(data, average, average_offset, start_night, end_night)
    
    if debug:
        print(f"Average offset: {average_offset}")
        print(f"Drawn plus average offset: {average_offset + average}")
        print(f"Drawn minus average offset: {average - average_offset}")
        print(f"Top: {highest[0]}")

    plot_data(data, time_data, average, average_offset, start_night, end_night, min_night_index, max_night_index, debug=debug)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="main.py", description='Finds clouds from a DAT file')
    parser.add_argument("-p", "--place", type=str, required=True, help="The URL to the DAT file")
    parser.add_argument('--list-places', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true', help="Shows unnecessary lines and gives logs")
    args = parser.parse_args()
    main(url=args.place, debug=args.verbose)
