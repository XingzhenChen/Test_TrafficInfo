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
    # 定义 CSV 文件列名
    csv_columns = ["Date", "Clones", "Views"]

    # 读取已有数据（如果文件存在）
    if os.path.exists(data_file_path):
        df = pd.read_csv(data_file_path)
    else:
        df = pd.DataFrame(columns=csv_columns)  # 创建空 DataFrame

    # 遍历 traffic_data，收集所有日期的 clones 和 views
    new_data = {}

    for repository_name, repository_data in traffic_data.items():
        # 处理 clones
        if "clones" in repository_data:
            for timestamp, metrics in repository_data["clones"].items():
                date_str = timestamp.strftime('%Y-%m-%d')
                if date_str not in new_data:
                    new_data[date_str] = [0, 0]  # 初始化
                new_data[date_str][0] = metrics[0]  # 记录 Clones

        # 处理 views
        if "views" in repository_data:
            for timestamp, metrics in repository_data["views"].items():
                date_str = timestamp.strftime('%Y-%m-%d')
                if date_str not in new_data:
                    new_data[date_str] = [0, 0]  # 初始化
                new_data[date_str][1] = metrics[0]  # 记录 Views

    # 更新 DataFrame
    for date, (clones, views) in new_data.items():
        if date in df["Date"].values:
            df.loc[df["Date"] == date, ["Clones", "Views"]] = [clones, views]
        else:
            df = pd.concat([df, pd.DataFrame([[date, clones, views]], columns=csv_columns)], ignore_index=True)

    # 按日期排序
    df = df.sort_values("Date")

    # 写回 CSV
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
def run_gitratra(token, data_path, repositories_file_path):
  print("Authentification...")
  g = None
  split_token = token.split(":")
  if (split_token[0] == "token"):
    g = Github(split_token[1])
  else:
    g = Github(split_token[1], getpass.getpass())
  repositories = read_repositories_names(repositories_file_path)
  # traffic_data = get_traffic_data("/home/xingzhen/AAA_Project_ProMax/GitHub_traffic_monitor/GiTraTra/output.txt")
  traffic_data = {}
  for repo_name in repositories:
    repo = g.get_user().get_repo(repo_name)
    update_repo(repo, traffic_data)
  print_summary(traffic_data)
  write_data(traffic_data, data_path)

def print_error_syntax():
    print("Possible syntaxes:")
    print("python run_generax.py token:<github_token> <repositories_list_file> <output_file>.")
    print("python run_generax.py username:<username> <repositories_list_file> <output_file>.")

def ReadPlot(csv_path):
  # 从CSV读取数据并画图
  # 读取CSV文件
  df = pd.read_csv(csv_path)

  # 确保'年-月-日'格式的日期正确解析
  df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')

  # 创建画布
  plt.figure(figsize=(10, 6))

  # 绘制Clones和Views的折线图
  plt.plot(df['Date'], df['Clones'], label='Clones', marker='o', linestyle='-')
  plt.plot(df['Date'], df['Views'], label='Views', marker='s', linestyle='-')

  # 设置X轴刻度间隔为每天
  plt.gca().xaxis.set_major_locator(mdates.DayLocator())
  # 设置X轴标签格式
  plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))

  # 旋转X轴标签以提高可读性
  plt.xticks(rotation=45)

  # 设置标题和标签
  plt.title('Clones and Views Over Time')
  plt.xlabel('Date')
  plt.ylabel('Count')

  # 显示图例
  plt.legend()

  # 自动调整布局，防止标签重叠
  plt.tight_layout()

  # 保存图表为PNG文件
  plt.savefig('TrafficPlot.png')

  # 显示图表
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
  data_path = sys.argv[3]
  run_gitratra(token, data_path, repositories_file_path)
  ReadPlot(data_path)
