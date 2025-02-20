import os
import sys
from github import Github
import pickle
from datetime import datetime
import getpass
import pandas as pd
import csv
import matplotlib.pyplot as plt
import matplotlib.dates as mdates



def write_data(traffic_data, data_file_path):
    
    csv_columns = ["Date", "Clones", "Views"]

    
    if os.path.exists(data_file_path):
        df = pd.read_csv(data_file_path)
    else:
        df = pd.DataFrame(columns=csv_columns) 

    
    new_data = {}

    for repository_name, repository_data in traffic_data.items():
        #  clones
        if "clones" in repository_data:
            for timestamp, metrics in repository_data["clones"].items():
                date_str = timestamp.strftime('%Y-%m-%d')
                if date_str not in new_data:
                    new_data[date_str] = [0, 0]  
                new_data[date_str][0] = metrics[0]  

        #  views
        if "views" in repository_data:
            for timestamp, metrics in repository_data["views"].items():
                date_str = timestamp.strftime('%Y-%m-%d')
                if date_str not in new_data:
                    new_data[date_str] = [0, 0] 
                new_data[date_str][1] = metrics[0] 

    
    for date, (clones, views) in new_data.items():
        if date in df["Date"].values:
            df.loc[df["Date"] == date, ["Clones", "Views"]] = [clones, views]
        else:
            df = pd.concat([df, pd.DataFrame([[date, clones, views]], columns=csv_columns)], ignore_index=True)


    df = df.sort_values("Date")


    df.to_csv(data_file_path, index=False)


"""
  Several helper functions for navigating into a list
  of lines
"""
def no_more_lines(reader):
  return reader[1] >= len(reader[0])

def pick_line(reader):
  if (no_more_lines(reader)):
    return None
  return reader[0][reader[1]][:-1]

def read_line(reader):
  if (no_more_lines(reader)):
    return None
  reader[1] = reader[1] + 1
  return reader[0][reader[1] - 1][:-1]

""" 
  Several functions to read Data from a file
"""
def read_metric_data(reader, repository_data):
  metrics_name = read_line(reader)[1:]
  metric_data = {}
  while (True):
    line = pick_line(reader)
    if (no_more_lines(reader) or line.startswith("#") or line.startswith(">")):
      break;
    line = read_line(reader)
    split = line.split(" ")
    timestamp = datetime.strptime(split[0], '%Y-%m-%d')
    count = int(split[1])
    uniques = int(split[2])
    metric_data[timestamp] = [count, uniques]
  repository_data[metrics_name] = metric_data

def read_repository_data(reader, traffic_data):
  repository = read_line(reader)[1:]
  traffic_data[repository] = {}
  while (not no_more_lines(reader) and pick_line(reader).startswith("#")):
    read_metric_data(reader, traffic_data[repository])

def read_traffic_data(data_file_path):
  traffic_data = {}
  lines = open(data_file_path).readlines()
  reader = [lines, 0]
  gitratra_format = read_line(reader)
  assert(gitratra_format == "gitratra_v1")
  while (reader[1] < len(reader[0])):
    read_repository_data(reader, traffic_data)
  return traffic_data  

def get_traffic_data(data_file_path):
  if (not os.path.isfile(data_file_path)):
    return {}
  else:
    print("File " + data_file_path + " already exists, loading existing traffic data...")
    return read_traffic_data(data_file_path)


"""
  Given a Repository object and a metric name ("view" or "clone"), 
  update our Data structure with a query to github
"""
def update_metric(repo, traffic_data, metric_name):
  metrics = None
  if (metric_name == "views"):
    metrics = repo.get_views_traffic()[metric_name]
  elif (metric_name == "clones"):
    metrics = repo.get_clones_traffic()[metric_name]
  else:
    assert(False)
  metric_data = traffic_data[repo.name][metric_name]
  for metric in metrics: 
    count = metric.count
    uniques = metric.uniques
    if (metric.timestamp in metric_data):
      # at the 14th oldest timestamp, the number of clones or views given by 
      # GitHub might decrease depending on the hour
      # We don't want to blindly erase,the existing value, but to take 
      # the max.
      count = max(count, metric_data[metric.timestamp][0])
      uniques = max(uniques, metric_data[metric.timestamp][1])
    assert(count >= uniques)
    metric_data[metric.timestamp] = [count, uniques]

"""
  Given a Repository object, update a Data object with
  queries to github
"""
def update_repo(repo, traffic_data):
  if (not repo.name in traffic_data):
    print("Adding new repository " + repo.name)
    traffic_data[repo.name] = {}
    traffic_data[repo.name]["clones"] = {}
    traffic_data[repo.name]["views"] = {}
  print("querying current traffic data from " + repo.name + "...")
  update_metric(repo, traffic_data, "clones")
  update_metric(repo, traffic_data, "views")

"""
  Briefly summarize the traffic information
  stored in the traffic data
"""
def print_summary(traffic_data):
  print("")
  for repo_name in traffic_data:
    repository_data = traffic_data[repo_name]
    print(repo_name)
    for metric_name in repository_data:
      total_uniques = 0
      total_count = 0
      metric_data = repository_data[metric_name]
      for timestamp in metric_data:
        metrics = metric_data[timestamp]
        total_count += metrics[0]
        total_uniques += metrics[1]
      print(metric_name + ": " + str(total_count))
      print("unique " + metric_name + ": " + str(total_uniques))
    print("")


def read_repositories_names(repositories_file_path):
  res = []
  lines = open(repositories_file_path).readlines()
  for line in lines:
    strip = line.strip()
    if (len(strip) > 0):
      res.append(strip)
  return res

"""
  Main function
"""
def run_gitratra(token, data_folder, repositories_file_path):
  print("Authentification...")
  g = None
  split_token = token.split(":")
  if (split_token[0] == "token"):
    g = Github(split_token[1])
  else:
    g = Github(split_token[1], getpass.getpass())
  repositories = read_repositories_names(repositories_file_path)

  
  for repo_name in repositories:
    traffic_data = {}
    repo = g.get_user().get_repo(repo_name)
    update_repo(repo, traffic_data)
    print_summary(traffic_data)
    data_file = os.path.join(data_folder, f"{repo_name}.csv")
    write_data(traffic_data, data_file)
    ReadPlot(repo_name, data_file)

def print_error_syntax():
    print("Possible syntaxes:")
    print("python run_generax.py token:<github_token> <repositories_list_file> <output_file>.")
    print("python run_generax.py username:<username> <repositories_list_file> <output_file>.")

def ReadPlot(repo_name, csv_path):
  
  df = pd.read_csv(csv_path)

  
  df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')


  plt.figure(figsize=(10, 6))


  plt.plot(df['Date'], df['Clones'], label='Clones', marker='o', linestyle='-')
  plt.plot(df['Date'], df['Views'], label='Views', marker='s', linestyle='-')


  plt.gca().xaxis.set_major_locator(mdates.DayLocator())

  plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))


  plt.xticks(rotation=46)


  plt.title('Clones and Views Over Time')
  plt.xlabel('Date')
  plt.ylabel('Count')


  plt.legend()


  plt.tight_layout()


  plot_path = os.path.join("./", f"{repo_name}_TrafficPlot.png")
  plt.savefig(plot_path)

  plt.show()


if (__name__== "__main__"):
  if (len(sys.argv) != 4):
    print_error_syntax()
    sys.exit(0)
  token = sys.argv[1]
  if (len(token.split(":")) != 2):
    print("ERROR: Invalid token or username string")
    print_error_syntax()
    sys.exit(1)
  repositories_file_path = sys.argv[2]
  data_folder = sys.argv[3]
  run_gitratra(token, data_folder, repositories_file_path)
  
