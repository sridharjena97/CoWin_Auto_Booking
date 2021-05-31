from typing import Counter
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import datetime
import requests
import hashlib
import base64
import time
import json
import re
import winsound
import threading

def line_break(): print("*"*55)

class CoWinBook():

    def __init__(self):
        try:    
            a = open("appsettings.json")
        except FileNotFoundError:
            self.collectDataFromCMD()
        else:  
            i = input("Do you want to load last settings? y/n: ")
            if i.lower()== "y":
                self.setVarFromJSON()
            else:
                self.collectDataFromCMD()
    # Collect data from cmd
    def collectDataFromCMD(self):
        self.mobile_no = self.collectMobile()
        # Request Session
        self.session =  requests.Session() 
        # intializing session
        self.getSession()
        self.user_id = self.select_beneficiaries()  # Selected Users for Vaccination 
        self.pincodes = self.collectPin()
        self.center_id = []  # Selected Vaccination Centers
        # Vaccination Center id and Session id for Slot Booking
        self.vacc_center = None
        self.vacc_session = None
        self.slot_time = None
        self.center_name = None
        # Dose 1 or Dose 2
        self.dose = self.collectDose()
        self.vaccine_name = self.collectVaccineName()

        # OTP Fetching method 
        self.otp = None

        # User Age 18 or 45
        self.age = self.collectAge()
        print(f"You fall in cat: {self.age}+")
        

        # Data for sending request
        self.data = {} 

        # Token Recieved from CoWIN
        self.bearerToken = None  # Session Token

        self.sleepinterval = self.collectSleep()
        self.vaccinetype = self.collectVaccineType()
        self.date = self.collectDate()
        # Login and Save Token in file( filename same as mobile no)
        
        # self.select_beneficiaries()
        self.writeJSON()
        # Start Looping the booking process
        self.booked = False
        while self.booked==False:
            self.request_slot(data)

    # validate and write collected data into JSON file
    def writeJSON(self):
        global data
        data = {
            "BeneficiaryIds": self.user_id,
            "mobile":self.mobile_no, 
            "age":self.age,
            "SleepIntervalInSeconds":self.sleepinterval,
            "MinimumVaccineAvailability":len(self.user_id),
            "DoseType":self.dose,
            "VaccineFeeType": self.vaccinetype,
            "VaccineName": self.vaccine_name,
            "VaccinationCentreName": "",
            "PINCodes": self.pincodes,
            "DateToSearch": self.date,
            "DaysToSearchFurther":4
        }
        with open("appsettings.json","w") as f:
            json.dump(data,f)

    # Collect Vaccine Name
    def collectVaccineName(self):
        print("1: Enter 1 for COVISHIELD\n2: Enter 2 for COVAXIN\n3: Enter 3 for SPUTNIK V")
        t = input("Enter your response(press enter to skip): ")
        if t=='1' or t=='2' or t=='3':
            if t =='1':
                return 'COVISHIELD'
            if t=='2':
                return 'COVAXIN'
            if t=='3':
                return 'SPUTNIK V'
        else:
            return ''

    # collect date
    def collectDate(self):
        while True:
            d = input("Enter date to search in dd-mm-yyyy format: ")
            d1 = d.split('-')
            if d1[0].isnumeric and d1[1].isnumeric and d1[2].isnumeric and 0<int(d1[0])<32 and 0<int(d1[1])<13 and len(d1[2])==4:
                return datetime.datetime(day=int(d1[0]), month=int(d1[1]),year=int(d1[2])).strftime("%d-%m-%Y")
            else:
                print("Invalid Date. Please try again..")
    # Collect vaccine type
    def collectVaccineType(self):
        print("1: Enter 1 for free\n2: Enter 2 for paid")
        t = input("Enter your response(press enter to skip): ")
        if t=='1' or t=='2':
            if t =='1':
                return 'Free'
            if t=='2':
                return 'Paid'
        else:
            return 'Free'


    # collect sleep interval
    def collectSleep(self):
        i = input("Enter sleep time after a reqest(press enter to skip): ")
        if i.isnumeric() and int(i)>20:
            return int(i)
        else:
            return 20
    # Collect Mobile No
    def collectMobile(self):
        while True:
            m = input("Enter your mobile no: ")
            if len(m)==10 and m.isnumeric():
                return m
            else:
                print("Invalid input. Please Try Again......\n")
    # Collect age from user
    def collectAge(self):
        age= int(input("Enter your age: "))
        if age<18:
            print("You are not eligible for vaccination")
        elif age>= 18:
            return 18 if age < 45 else 45
        else:
            print("Invalid input")

    # Collect dose from user
    def collectDose(self):
        while True:
            dose = int(input("\nSelect dose type:\n1. Enter 1 for dose-1\n2. Enter 2 for dose-2\nEnter your response here: "))
            if dose == 1 or dose == 2:
                print("you have selected dose-", dose)
                return dose
                
            else:
                print("Invalid input")
                continue

    # Collect pincodes from user
    def collectPin(self):
        pincode_list= []
        while True:
            pin = input("\nEnter a pincode: ")
            if len(pin)==6:
                pincode_list.append(pin)
                i = input("Enter 'y' to add more pincodes or press enter to continue: ")
                if i.lower()=='y':
                    print(pincode_list)
                    continue
                else:
                    print("\nSelected Pincodes are:", pincode_list)
                    return pincode_list
            else:
                print("invalid input")

    # Validate pin codes  
    def validatePinCode(self, pin_codes_list):
        for pin in pin_codes_list:
            if len(pin)!=6:
                return False
        return True 

    def setVarFromJSON(self):
        # checking json data
        def checkData(data):
            if data["BeneficiaryIds"]==[] or data["BeneficiaryIds"]==None:
                raise Exception("Error in Settings: Beneficiary ID should not be blank")
            elif data["mobile"]== "" or data["mobile"]==None:
                raise Exception("Error in Settings: Mobile number Should not left blank")
            elif len(data["mobile"])!=10:
                raise Exception("Error in Settings: Invalid mobile number")
            elif data["age"]=="" or data["age"]==None:
                raise Exception("Error in Settings: Please define age")
            elif data["age"]<18:
                raise Exception("Error in Settings: This age is not eligible for vaccination")
            elif data["SleepIntervalInSeconds"]==None or data["SleepIntervalInSeconds"]=="":
                raise Exception("Error in Settings: Please define sleep interval")
            elif data["MinimumVaccineAvailability"]==None or data["MinimumVaccineAvailability"]=="":
                raise Exception("Error in Settings: Please define MinimumVaccineAvailability")
            elif data["DoseType"] != 1 and data["DoseType"]!= 2:
                raise Exception("Error in Settings: Invalid dose type")
            elif data["VaccineFeeType"]=='free' or data["VaccineFeeType"]=='paid':
                raise Exception("Error in Settings: Invalid vaccine type")
            elif not self.validatePinCode(data["PINCodes"]):
                raise Exception("Error in Settings: Please define dose type") 
        # Opening JSON file
        try:
            with open("appsettings.json") as f:
                data = json.load(f)
            checkData(data)
        except Exception as e:
            print(e)
        self.mobile_no = str(data["mobile"])
        self.pincodes = data["PINCodes"] # Area Pincode
        self.center_id = []  # Selected Vaccination Centers
        self.user_id = data["BeneficiaryIds"]  # Selected Users for Vaccination 
        self.vaccine_name = data["VaccineName"]
        # Vaccination Center id and Session id for Slot Booking
        self.vacc_center = None
        self.vacc_session = None
        self.slot_time = None
        self.center_name = None
        # Dose 1 or Dose 2 ( default : 1)
        self.dose = data["DoseType"]

        # OTP Fetching method 
        self.otp = None

        # User Age 18 or 45
        self.age = 18 if int(data["age"]) < 45 else 45
        # print(self.age)
        # Request Session
        self.session =  requests.Session() 

        # Data for sending request
        self.data = {} 

        # Token Recieved from CoWIN
        self.bearerToken = None  # Session Token

    
        # Login and Save Token in file( filename same as mobile no)
        self.getSession()
        # self.select_beneficiaries()

        # Start Looping the booking process
        self.booked = False
        while self.booked==False:
            self.request_slot(data)

    
    # select Beneficiary
    def select_beneficiaries(self):

        response = self.session.get('https://cdn-api.co-vin.in/api/v2/appointment/beneficiaries').json()

        USERS = []
        index = []
        selected_user_ID = set()
        selected_users = set()

        if not response.get('beneficiaries',[]):
            print("No user added in beneficiaries. Please visit cowin and register a member to continue.\n Exiting software.............")
            exit()
        # print(json.dumps(response, indent=3))
        counter = 1
        for user in response.get('beneficiaries'):
            user_dict = {}
            user_name = user.get("name")
            reference_id = user.get("beneficiary_reference_id")
            user_dict["index"] = counter
            user_dict["user_name"] = user_name
            user_dict["reference_ID"] = reference_id
            USERS.append(user_dict)
            index.append(counter)
            counter+=1
        isNotSelected = True
        line_break()
        print("Please select beneficiaries from below:\n")
        while isNotSelected:
            for data in USERS:
                print(f"{data['index']}: Press {data['index']} to Select {data['user_name']} ")
            selection = input("\n Enter Your response: ")
            if int(selection) in index:
                for data in USERS:
                    if int(selection)== data['index']:
                        selected_user_ID.add(data['reference_ID'])
                        selected_users.add(data['user_name'])
                else:
                    i = input("Do you want to add more? Enter 'y' or press enter to continue: ")
                    if i.lower()=="y":
                        continue
                    else:
                        print("you have selected", selected_users)
                        isNotSelected = False
            else:
                print("Invalid Selection\n")
            
         
        return list(selected_user_ID)

    # Set Header in self.session = requests.Session()
    def set_headers(self):
        ua = UserAgent()
        self.session.headers.update({
            'User-Agent': ua.random,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/json',
            'Origin': 'https://selfregistration.cowin.gov.in',
            'Connection': 'keep-alive',
            'Referer': 'https://selfregistration.cowin.gov.in/',
            'TE': 'Trailers',
        })

    # returning self.data 
    def get_data(self):
        return json.dumps(self.data).encode('utf-8')

    # Save Token after login to CoWIN
    def putSession(self):
        with open(f"{self.mobile_no}.log", "w") as f:
            f.write(self.bearerToken)
            

    # Get Token saved in file for relogin and use
    def getSession(self):
        self.set_headers()
        try:
            with open(f"{self.mobile_no}.log", "r") as f:
                self.bearerToken = f.read()
            self.session.headers.update({
                    'Authorization': 'Bearer {}'.format(self.bearerToken)
                })
            self.session.get('https://cdn-api.co-vin.in/api/v2/appointment/beneficiaries').json()
        except (FileNotFoundError,json.decoder.JSONDecodeError):
            self.login_cowin()
            

    # Login to selfregistration.cowin.gov.in/
    def login_cowin(self):

        self.data = {
        "secret":"U2FsdGVkX1+gGN13ULaCVtLSWmsyZwAdXXTIAvLQp2HOXrIBCcq0yyOZQqzzfiFiEYs7KoAOTK2j4qPF/sEVww==",
        "mobile": self.mobile_no
            }
    
        response = self.session.post('https://cdn-api.co-vin.in/api/v2/auth/generateMobileOTP',data=self.get_data())

        otpSha265 = self.get_otp()

        txn_id = response.json()['txnId']

        self.data = {
                        "otp":otpSha265,
                        "txnId": txn_id
                                    }
        
        response = self.session.post('https://cdn-api.co-vin.in/api/v2/auth/validateMobileOtp',data=self.get_data())
        
        self.bearerToken = response.json()['token']

        self.session.headers.update({
            'Authorization': 'Bearer {}'.format(self.bearerToken)
        })
        self.putSession() 

    # Request for OTP 
    def get_otp(self):
        def play():
            for i in range(10):
                winsound.Beep(500,200)

        a= threading.Thread(target=play)
        a.start()
        print(f"Otp sent to your mobile phone {self.mobile_no}")
        otp = input("\nEnter OTP : ")

        return hashlib.sha256(otp.encode('utf-8')).hexdigest()
   
    # Request for Current Slot Deatails ( Private Request )
    def request_slot(self, data):
        # def extractDate(date):
        #     temp = date.split("-")
        #     return datetime.datetime(day=int(temp[0]), month=int(temp[1]), year=int(temp[2]))

        # base = extractDate(data["DateToSearch"])
        # date_list = [base + datetime.timedelta(days=x) for x in range(int(data["DaysToSearchFurther"]))]
        # date_str = [x.strftime("%d-%m-%Y") for x in date_list]
        for pincode in self.pincodes:
            line_break()
            print(f"Searching for PinCode- {pincode}")
            response = self.session.get(f'https://cdn-api.co-vin.in/api/v2/appointment/sessions/calendarByPin?pincode={pincode}&date={data["DateToSearch"]}')

            if response.ok:
                # print(response.json())
                if self.check_slot(response.json(),data=data, pincode=pincode):
                    self.booked = True
                    return True
                else:
                    continue
            elif response.status_code == 401:
                print("Re-login Account : " + datetime.datetime.now().strftime("%H:%M:%S") + " 🤳")
                self.login_cowin()
                self.request_slot()
            else:
                print("Error Fetching slot:")
                print(f"resp_Code = {response.status_code} and MSG:{response.json()}")
            line_break()
        print("Last Checked  ✅ : " + datetime.datetime.now().strftime("%H:%M:%S") + " 🕐")
        time.sleep(int(data["SleepIntervalInSeconds"]))
        # When last Checked
        

    # Check Slot availability 
    def check_slot(self,response, data, pincode):

        for center in response.get('centers',[]):
            if center ==[]:
                print(f"[Warning] No Centers found at pincode-{pincode}")
            else:
                for session in center.get('sessions',[]):
                    self.vacc_center = center.get('center_id')
                    self.vacc_session = session.get("session_id")
                    self.slot_time = session.get('slots')[0]

                    self.center_name = center.get('name')
                    center_pin = center.get('pincode')
                    capacity = session.get(f'available_capacity_dose{data["DoseType"]}')
                    session_date = session.get('date')
                    vaccine_name = session.get('vaccine')
                    vaccine_type = center.get('fee_type')
                    if data["VaccineName"] != "":
                        if int(session.get('min_age_limit')) == self.age and data["VaccineFeeType"]==vaccine_type and data["VaccineName"]== vaccine_name:
                            if capacity >= int(data["MinimumVaccineAvailability"]):
                                MSG = f'💉 {capacity} {vaccine_name} / {session_date} / {self.center_name} 📍{center_pin}'

                                # Send Notification via Termux:API App
                                print("Hurry Centers Available\n",MSG)
                            
                                BOOKED = self.book_slot()
                                if BOOKED:
                                    print("Shutting Down CoWin Script 👩‍💻 ")
                                    return True
                            else:
                                print(f"[info] Sorry {capacity} Vaccine Found found at {self.center_name} on {session_date}.")
                        else:
                            continue
                    elif int(session.get('min_age_limit')) == self.age and data["VaccineFeeType"]==vaccine_type:
                        if capacity >= int(data["MinimumVaccineAvailability"]):
                            MSG = f'💉 {capacity} {vaccine_name} / {session_date} / {self.center_name} 📍{center_pin}'

                            # Send Notification via Termux:API App
                            print("Hurry Centers Available\n",MSG)
                        
                            BOOKED = self.book_slot()
                            if BOOKED:
                                print("Shutting Down CoWin Script 👩‍💻 ")
                                return True
                        else:
                            print(f"[info] Sorry {capacity} Vaccine Found found at {self.center_name} on {session_date}.")
                    else:
                        continue
        else:
            print("[Warning!] No vaccination center found as per your search! Try to change search criteria.")
            return False
                    
                        
                

        
        

    # Get Solved Captcha in String
    def get_captcha(self):

        model = "eyJNTExRTExRTExRTExMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTExRTExRWk1MTFFMTFFMTFFMTFFaIjogIjAiLCAiTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTFoiOiAiMSIsICJNTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExMUUxMTFFMTFFaIjogIjIiLCAiTUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTExMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExMUUxMUUxMUUxMUUxMUUxMUUxMTExRTExRTExRTExRTExRTExRTExMTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAiMyIsICJNTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRWk1MTFFMTExRTExRTExRTExRTExRTExRTExMUUxMTFFMTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRWiI6ICI0IiwgIk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMTExMUUxMTFFMTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTExRTExRTExRTExRTExRWiI6ICI1IiwgIk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaIjogIjYiLCAiTUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTExRTExRTExMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFaTUxMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExMTExRTExRTExRTExRTExRTExMUUxMTFFMTFFMTFFMTExRWiI6ICI3IiwgIk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExMUUxMUUxMUUxMUUxMTExMUUxMUUxMUUxMUUxMTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExMUUxMUUxMUUxMUUxMUUxMUVoiOiAiOCIsICJNTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaIjogIjkiLCAiTUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUVpNTExMUUxMUUxMUUxMUUxMUUxMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTExRWiI6ICJBIiwgIk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUVpNTExRTExRTExRTExRTExMUUxMUUxMUUxMUVpNTExMUUxMTExMUUxMTFFMTFFMTFFMTFFMTFFMTFFaIjogIkIiLCAiTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAiQyIsICJNTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFaIjogIkQiLCAiTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaIjogIkUiLCAiTUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUVoiOiAiRiIsICJNTExRTExRTExRTExMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMWiI6ICJHIiwgIk1MTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWiI6ICJIIiwgIk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAibCIsICJNTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWiI6ICJKIiwgIk1MTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMTExMUVpNTExRTExRTExRTExMUUxMUUxMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWiI6ICJLIiwgIk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAiTCIsICJNTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRWiI6ICJNIiwgIk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMWk1MTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAiTiIsICJNTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExRWiI6ICJPIiwgIk1MTFFMTFFMTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFaIjogIlAiLCAiTUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTExRTExMUUxMUUxMUUxMUUxMUVpNTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTExMTFFMTFFMTFFaIjogIlEiLCAiTUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMTFFMTFFMTFFaTUxMTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFaTUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFaIjogIlIiLCAiTUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAiUyIsICJNTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWiI6ICJUIiwgIk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaIjogIlUiLCAiTUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaIjogIlYiLCAiTUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAiVyIsICJNTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFaIjogIlgiLCAiTUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFoiOiAiWSIsICJNTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMTFFMTFFMTFFMTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRWiI6ICJaIiwgIk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExRWk1MTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaIjogImEiLCAiTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRWiI6ICJiIiwgIk1MTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExMUUxMUUxMUVoiOiAiYyIsICJNTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAiZCIsICJNTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTExRWk1MTFFMTFFMTFFMTFFMTFFaTUxMUUxMTExRTExRTExRWiI6ICJlIiwgIk1MTFFMTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFaTUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTExRTExRTExMUUxMTExRTExRTExMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaIjogImYiLCAiTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMTFFMTExRTExRTExRTExMUUxMUUxMUUxMUUxMTExRTExRTExRTExRTExRTExMUUxMTFFMTFFMTExRTExMUVpNTExRTExRTExRTExRTExRTExRTExRTExRWiI6ICJnIiwgIk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExMUUxMUVoiOiAiaCIsICJNTExRTExMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTFpNTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUVpNTExMTFFMTFFMTFFMTFFMTFFMTFFMTFFaIjogImkiLCAiTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExMUUxMUUxMUUxMUUxMUUxMTFFMTExMUUxMUVpNTExMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAiaiIsICJNTExRTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAiayIsICJNTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTExRTExRWk1MTExaIjogIm0iLCAiTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAibiIsICJNTExRTExRTExRTExRTExRTExRTExRWk1MTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAibyIsICJNTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExMUUxMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMTExMUUxMTFFMTFFMTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxaTUxMUUxMUUxMUUxMUUxMTFFMTExRTExMUUxMUVoiOiAicCIsICJNTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAicSIsICJNTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExaTUxMTFoiOiAiciIsICJNTExMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMTExRTExRTExRTExMUUxMUVoiOiAicyIsICJNTExRTExRTExRTExRTExMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFaTUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTExRTExRTExRWiI6ICJ0IiwgIk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMTExMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaIjogInUiLCAiTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTExRTExMUVoiOiAidiIsICJNTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTExRWk1MTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExMUUxMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMWiI6ICJ3IiwgIk1MTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMTFFaIjogIngiLCAiTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFaTUxMUUxMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMUVoiOiAieSIsICJNTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaIjogInoifQ=="
        
        # Send request for Captcha    
        data = '{}'
        response = self.session.post('https://cdn-api.co-vin.in/api/v2/auth/getRecaptcha', data=data)

        if not response.ok:
            self.login_cowin()
            return self.get_captcha()

        # Get Captcha Data from Json
        svg_data = response.json()['captcha']


        soup = BeautifulSoup(svg_data,'html.parser')

        model = json.loads(base64.b64decode(model.encode('ascii')))
        CAPTCHA = {}

        for path in soup.find_all('path',{'fill' : re.compile("#")}):

            ENCODED_STRING = path.get('d').upper()
            INDEX = re.findall('M(\d+)',ENCODED_STRING)[0]

            ENCODED_STRING = re.findall("([A-Z])", ENCODED_STRING)
            ENCODED_STRING = "".join(ENCODED_STRING)

            CAPTCHA[int(INDEX)] =  model.get(ENCODED_STRING)

        CAPTCHA = sorted(CAPTCHA.items())
        CAPTCHA_STRING = ''

        for char in CAPTCHA:
            CAPTCHA_STRING += char[1]

        return CAPTCHA_STRING

    # Book Slot for Vaccination
    def book_slot(self):

        
        captcha = self.get_captcha()

        self.data = {
            "center_id":self.vacc_center ,
            "session_id":self.vacc_session,
            "beneficiaries":self.user_id,
            "slot":self.slot_time,
            "captcha": captcha,
            "dose": self.dose
            }

        response = self.session.post('https://cdn-api.co-vin.in/api/v2/appointment/schedule',data=self.get_data())

        status =  response.status_code
        
        if status == 200:
            line_break()
            print(f"🏥 Appointment scheduled successfully!!🥳 at-{self.center_name} on slot - {self.slot_time}\n")
            res = response.json()
            result = res.get("appointment_confirmation_no")
            print(f"Your Appointment ID is {result}")
            line_break()
            with open(f"{self.mobile_no}_Booking_ID.txt","a") as f:
                f.write(f"\nYour Appointment ID is {result} booked on {datetime.datetime.now()}")
            # self.data = {"appointment_id" : result}
            # response = self.session.post('https://cdn-api.co-vin.in/api/v2/appointment/appointmentslip/download',data=self.get_data())
            # with open(f"{self.mobile_no}_appoint_slip_{result[:5]}.pdf", "wb") as f:
            #     f.write(response)
            return True
        elif status == 409:
            print("This vaccination center is completely booked for the selected date 😥")
            return False
        elif status == 401:
            self.login_cowin()
            self.book_slot()
        else:
            print("Error in Booking Slot")
            print(f'{status} : {response.json()}')
            return False
    

if __name__ == '__main__':

    line_break()
    print("Welcome to CoWin Auto Slot Booking.....")
    line_break()
    cowin = CoWinBook()

