from selenium import webdriver
from bs4 import BeautifulSoup
from datetime import datetime
import requests
import time
import smtplib
import random
import json
import os

def readJson(path):
    with open(path, "r") as f:
        return json.loads(f.read())

def sendEmail(sentFrom, to, emailText, cred):
    server = smtplib.SMTP_SSL(cred['smtp'], cred['smtpPort'])
    server.ehlo()
    server.login(cred['login'], cred['password'])
    server.sendmail(sentFrom, to, emailText)
    server.close()

config = readJson(os.path.join("./config.json"))

driver = webdriver.Chrome(config['chromeDriverPath'])
time.sleep(5)

f = open(config['logFile'], "a")
f.write("============================================================= \r\n")
f.write("Starting to monitor UPS devices on %s\r\n" % datetime.now())

upsIps = config['upsIps']

for upsIp in upsIps:
    f.write("Trying to scrub data for UPS with IP:  %s\r\n" % upsIp)
    try:
        driver.implicitly_wait(10)

        driver.get("http://" + upsIp + "/logon.htm")
        driver.find_element_by_name("login_username").send_keys(config['upsLogin'])
        driver.find_element_by_name("login_password").send_keys(config['upsPassword'])
        driver.find_element_by_name("submit").click()

        driver.find_element_by_link_text("Home").click()
        content = driver.page_source
        soup = BeautifulSoup(content)

        # Get Ups ip
        upsScrubedIp = soup.findAll('td', {"class": "update"})[0].text
        f.write("Logged in on UPS with IP:  %s\r\n" % upsScrubedIp)
    except Exception as e:
        upsScrubedIp = 'Not Set'
        f.write("Could not logged in on UPS with error:  %s\r\n" % str(e))

    # Generate event logs for understanding what is going on in UPS env
    try:
        envLog = []
        for parentTd in soup.findAll('td', id="env"):
            for td in parentTd.findAll('td'):
                if td.text[0:5] != 'Smart' and td.text != 'Environment' and len(td.text) > 1:
                    envLog.append(td.text.replace("\xa0", "").strip())
                    # print((td.text.replace("\xa0", "")).strip())
        f.write("Event logs are generated:  %s\r\n" % str(envLog))
    except Exception as e:
        envLog = []
        f.write("Could not get event logs with error:  %s\r\n" % str(e))

    # Get Load in Watts in percents
    time.sleep(5)
    try:
        elem = driver.find_element_by_link_text("UPS")
        elem.click()

        content = driver.page_source
        soup = BeautifulSoup(content)
        x = soup.findAll('tbody')

        loadInWatts = x[10].findAll('td')[-1].contents[0].strip('%').strip()

        f.write("Load in watts:  %s\r\n" % str(loadInWatts))
    except Exception as e:
        loadInWatts = 'Not Set'
        f.write("Could not get load in watts with error:  %s\r\n" % str(e))

    # Get Battery Capacity in percents
    try:
        batteryCapacity = x[12].findAll('td')[-1].contents[0].strip('%').strip()

        f.write("Battery capacity:  %s\r\n" % str(batteryCapacity))
    except Exception as e:
        batteryCapacity = 'Not Set'
        f.write("Could not get battery capacity with error:  %s\r\n" % str(e))

    # Get Input Voltage
    try:
        inputVoltage = x[8].findAll('tr')[20].findAll('td')[-1].contents[0].strip()

        f.write("Input Voltage:  %s\r\n" % str(inputVoltage))
    except Exception as e:
        inputVoltage = 'Not Set'
        f.write("Could not get input voltage with error:  %s\r\n" % str(e))

    # Get Output Voltage
    try:
        outputVoltage = x[8].findAll('tr')[21].findAll('td')[-1].contents[0].strip()

        f.write("Output Voltage:  %s\r\n" % str(outputVoltage))
    except Exception as e:
        outputVoltage = 'Not Set'
        f.write("Could not get output voltage with error:  %s\r\n" % str(e))

    # Get Runtime Remaining
    try:
        runtimeRemaining = x[8].findAll('tr')[23].findAll('td')[-1].contents[0].strip()

        f.write("Runtime Remaining:  %s\r\n" % str(runtimeRemaining))
    except Exception as e:
        runtimeRemaining = 'Not Set'
        f.write("Could not get runtime remaining with error:  %s\r\n" % str(e))

   # Get Temperature in C
    try:
        time.sleep(5)
        elem = driver.find_element_by_link_text("Environment")
        elem.click()
        time.sleep(5)
        content = driver.page_source
        soup = BeautifulSoup(content)
        x = soup.findAll('tbody')

        temperatureInC = x[7].findAll('td')[-2].contents[0].strip('C').strip().strip('°')

        f.write("Temperature In C:  %s\r\n" % str(temperatureInC))
    except Exception as e:
        temperatureInC = 'Not Set'
        f.write("Could not get temperature in C with error:  %s\r\n" % str(e))

    # Get Humidity info
    try:
        humidity = x[7].findAll('td')[-1].contents[0]

        f.write("Humidity:  %s\r\n" % str(humidity))
    except Exception as e:
        humidity = 'Not Set'
        f.write("Could not get humidity with error:  %s\r\n" % str(e))

    allIsOkCheckOne = [i for i, x in enumerate(envLog) if x == 'No Alarms Present']
    allIsOkCheckTwo = [i for i, x in enumerate(envLog) if x == 'UPS is online.']

    subject = 'UPS ' + upsScrubedIp
    body = "Logs: " + ", ".join(envLog) + "\n"
    body = body + "Load in Watts: " + loadInWatts + '%' + "\n"
    body = body + 'Battery Capacity: ' + batteryCapacity + '%' + "\n"
    body = body + 'Input Voltage: ' + inputVoltage + "\n"
    body = body + 'Output Voltage: ' + outputVoltage + "\n"
    body = body + 'Runtime Remaining: ' + runtimeRemaining + "\n"
    body = body + 'Temperature of server Room: ' + temperatureInC + " C" + "\n"
    body = body + 'Humidity: ' + humidity + "\n"

    sentFrom = config['email']['sentFrom']

    if (not (len(allIsOkCheckOne) == 2 and len(allIsOkCheckTwo) == 1)):
        to = config['email']['criticalReceivers']
        emailText = """\
From: %s
To: %s
Subject: %s

Alert: Something went wrong with UPS. \n
%s
        """ % (sentFrom, ", ".join(to), subject, body)

        try:
            sendEmail(sentFrom, to, emailText, config['email'])

            f.write("An error ALERT email was sent from " + sentFrom + " to " + str(to) + " with subject " + str(subject) + "\r\n")
        except Exception as e:
            f.write("Could not send an email concerning to ups bad log with error:  %s\r\n" % str(e))
    elif (str(temperatureInC) != 'Not Set' and int(float(temperatureInC)) > 23):
        to = config['email']['warningReceivers']
        emailText = """\
From: %s
To: %s
Subject: %s

Warning: The temperature of the server room exceeds 23 C! \n
%s
        """ % (sentFrom, ", ".join(to), subject, body)

        try:
            sendEmail(sentFrom, to, emailText, config['email'])

            f.write("A temperature WARNING email was sent from " + sentFrom + " to " + str(to) + " with subject " + str(subject) + "\r\n")
        except Exception as e:
            f.write("Could not send an email concerning to server room tempreture with error:  %s\r\n" % str(e))
    else:
        to = config['email']['infoReceivers']
        emailText = """\
From: %s
To: %s
Subject: %s

This is an information message about the state of UPS, which is sent randomly.\n
%s
        """ % (sentFrom, ", ".join(to), subject, body)
        try:
            if random.randint(1, 500) == 168:

                sendEmail(sentFrom, to, emailText, config['email'])

                f.write("A random INFO email was sent from " + sentFrom + " to " + str(to) + " with subject " + str(subject) + "\r\n")
        except Exception as e:
            f.write("Could not send an email concerning to server room envoirenment with error:  %s\r\n" % str(e))

    time.sleep(5)
    try:
        elem = driver.find_element_by_link_text("Log Off")
        elem.click()

        f.write("The Ups is logged off\r\n\n\n\n\n")
        time.sleep(5)
    except Exception as e:
        f.write("Could not log off with error:  %s\r\n" % str(e))


driver.quit()

f.write("============================================================= \r\n")
f.close()
