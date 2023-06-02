import requests
import yaml
import random
from datetime import datetime, timedelta
import json
import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
import time

time_zone = 8  # 时区

# 两天后日期
key = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][(datetime.now().weekday() + 2) % 7]

def get_one_study_room_seat(floor):
    if floor == 2:
        # 10093-10472
        return random.randint(10093, 10472)
    if floor == 4:
        # 28868-29237
        return random.randint(28868, 29237)


class SeatAutoBooker:
    def __init__(self):
        self.json = None
        self.resp = None
        self.user_data = None

        self.un = os.environ["SCHOOL_ID"].strip()  # 学号
        print("使用用户：{}".format(self.un))
        self.pd = os.environ["PASSWORD"].strip()  # 密码
        self.SCKey = None
        try:
            self.SCKey = os.environ["SCKEY"]
        except KeyError:
            print("没有Server酱的key,将不会推送消息")

        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(service=Service('/usr/local/bin/chromedriver'), options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10, 0.5)
        self.cookie = None

        with open("_config.yml", 'r') as f_obj:
            cfg = yaml.safe_load(f_obj)
            self.start_time = cfg['start-time']
            self.book_url = cfg['target']
            self.headers = cfg['headers']
            self.type = cfg[key]['type']
            if self.type == "自定义":
                self.seats = cfg['自定义']

    def book_favorite_seat(self, start_hour, duration):
        """
        预约后天的座位
        :param start_hour: start time, for tomorrow.
        :param duration: dwell time (hours)
        :return: CODE, MASSAGE
        CODE: 'ok' for success
        """
        # 获取座位
        seats = []
        if self.type == "自定义":
            seats = self.seats
        elif self.type == "二楼自习室":
            seats = [get_one_study_room_seat(2)]
        elif self.type == "四楼自习室":
            seats = [get_one_study_room_seat(4)]
        # 相关post参数生成
        today_0_clock = datetime.strptime(datetime.now().strftime("%Y-%m-%d 00:00:00"), "%Y-%m-%d %H:%M:%S")
        book_time = today_0_clock + timedelta(days=2) + timedelta(hours=start_hour)
        delta = book_time - self.start_time
        total_seconds = delta.days * 24 * 3600 + delta.seconds

        seat = random.choice(seats)
        data = f"beginTime={total_seconds}&duration={3600 * duration}&&seats[0]={seat}&seatBookers[0]={self.user_data['uid']}"

        # post
        headers = self.headers
        headers['Cookie'] = self.cookie
        print(data)
        self.resp = requests.post(self.book_url, data=data, headers=headers)
        self.json = json.loads(self.resp.text)
        return self.json["CODE"], self.json["MESSAGE"] + " 座位:{}".format(seat)

    def login(self):
        pwd_path_selector = """//*[@id="react-root"]/div/div/div[1]/div[2]/div/div[1]/div[2]/div/div/div/div/div[1]/div[2]/div/div[3]/div/div[2]/input"""
        button_path_selector = """//*[@id="react-root"]/div/div/div[1]/div[2]/div/div[1]/div[2]/div/div/div/div/div[1]/div[3]"""

        try:
            self.driver.get("https://hdu.huitu.zhishulib.com/")
            self.wait.until(EC.presence_of_element_located((By.NAME, "login_name")))
            self.wait.until(EC.presence_of_element_located((By.XPATH, pwd_path_selector)))
            self.wait.until(EC.presence_of_element_located((By.XPATH, button_path_selector)))
            self.driver.find_element(By.NAME, 'login_name').clear()
            self.driver.find_element(By.NAME, 'login_name').send_keys(self.un)  # 传送帐号
            self.driver.find_element(By.XPATH, pwd_path_selector).clear()
            self.driver.find_element(By.XPATH, pwd_path_selector).send_keys(self.pd)  # 输入密码
            self.driver.find_element(By.XPATH, button_path_selector).click()
            time.sleep(5)
            cookie_list = self.driver.get_cookies()
            self.cookie = ";".join([item["name"] + "=" + item["value"] + "" for item in cookie_list])
            self.headers['Cookie'] = self.cookie

        except Exception as e:
            print(e.__class__.__name__ + "无法登录")
            return -1
        return 0

    def get_user_info(self):
        # 获取UID
        headers = self.headers
        headers['Cookie'] = self.cookie
        try:
            resp = requests.get("https://hdu.huitu.zhishulib.com/Seat/Index/searchSeats?LAB_JSON=1",
                                headers=headers)
            self.user_data = resp.json()['DATA']
            _ = self.user_data['uid']
        except Exception as e:
            print(self.user_data)
            print(e.__class__.__name__ + ",获取用户数据失败")
            return -1
        print("获取用户数据成功")
        return 0

    def wechatNotice(self, message, desp=None):
        if self.SCKey != '':
            url = 'https://sctapi.ftqq.com/{0}.send'.format(self.SCKey)
            data = {
                'title': message,
                desp: desp,
            }
            try:
                r = requests.post(url, data=data)
                if r.json()["data"]["error"] == 'SUCCESS':
                    print("Server酱通知成功")
                else:
                    print("Server酱通知失败")
            except Exception as e:
                print(e.__class__, "推送服务配置错误")

if __name__ == "__main__":
    if datetime.now().hour == 18 - time_zone :  
        time.sleep(3300)
    if datetime.now().hour == 19 - time_zone :  
        # hold on
        slep=60-datetime.now().minute
        nap=datetime.now().second
        print("图书馆预约时间未到，我将等待约{}分钟后运行，现在的时间是：".format(slep))
        print (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        time.sleep(60*slep-nap-24)
        print("我醒了，即将开始预约，现在的时间是：")
        print (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    else:                                                                    
        print("还未到预约时间！请稍后再试！")
        print (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        exit(0)
    with open("_config.yml", 'r') as f_obj:
        cfg = yaml.safe_load(f_obj)

    # 判断是否启用
    if not cfg[key]['启用']:
        print("后天无预约")
        exit(0)

    print("尝试预约,开始时间：{}，持续时间：{}小时".format(cfg[key]['开始时间'], cfg[key]['持续小时数']))
 
    s = SeatAutoBooker()
    if not s.login() == 0:
        s.driver.quit()
        exit(-1)
    if not s.get_user_info() == 0:
        s.driver.quit()
        exit(-1)
    stat, msg = s.book_favorite_seat(cfg[key]['开始时间'], cfg[key]['持续小时数'])
    if stat != "ok":
        for i in range(3):
            if i == 0: print("第一次勇敢牛牛！")
            if i == 1: print("第二次勇敢牛牛！")
            if i == 2: print("终极勇敢牛牛！")
            print (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))               
            stat, msg = s.book_favorite_seat(cfg[key]['开始时间'], cfg[key]['持续小时数'])
            print(stat, msg)
            time.sleep(6)
            if stat == "ok":
                print ("牛不灭！牛最强！")
                print (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
                break
    print("{}".format("勇敢牛牛，不怕困难！" if stat == "ok" else "npk48!"))
    s.wechatNotice("{}".format("勇敢牛牛，不怕困难！" if stat == "ok" else "npk48!"))
    print(stat, msg)
    s.driver.quit()
