from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import datetime
import requests
import hashlib
import base64
import time
import json
import re

from requests.models import Response


def line_break(): print("*"*55)

class CoWinBook():

    def __init__(self):
        # Check Pincode
        def validatePinCode(pin_codes_list):
            for pin in pin_codes_list:
                if len(pin)!=6:
                    return False
            return True

        # checking json data
        def checkData(data):
            if data["BeneficiaryIds"]==[] or data["BeneficiaryIds"]==None:
                raise Exception("Error in Settings: Beneficiary ID should not be blank")
            elif len(data["BeneficiaryIds"])>1:
                raise Exception("Error in Settings: Only one reference id is allowed")
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
            elif not validatePinCode(data["PINCodes"]):
                raise Exception("Error in Settings: Please define dose type")


        try:
            with open("appsettings.json") as f:
                data = json.load(f)
            checkData(data)
        except Exception as e:
            print(e)
        else:
            self.mobile_no = str(data["mobile"]) #USer's mobile number
            self.pincodes = data["PINCodes"] # Area Pincode
            self.center_id = []  # Selected Vaccination Centers
            self.user_id = data["BeneficiaryIds"]  # Selected Users for Vaccination 

            # Vaccination Center id and Session id for Slot Booking
            self.vacc_center = None
            self.vacc_session = None
            self.slot_time = None

            # Dose 1 or Dose 2 ( default : 1)
            self.dose = data["DoseType"] # 1st or 2nd dose

            # OTP Fetching method 
            self.otp = None

            # User Age 18 or 45
            self.age = 18 if int(data["age"]) < 45 else 45 # setting correct age

            # Request Session
            self.session =  requests.Session() # Requesting a new seassion

            # Data for sending request
            self.data = {} # Data to be sent with get or post request

            # Token Received from CoWIN
            self.bearerToken = None  # Session Token

        
            # Login and Save Token in file( filename same as mobile no)
            self.getSession()

            #Getting Appointment ID
            self.appointment_id = self.get_appointment(data)
            # Start Looping the booking process
            self.booked = False
            while self.booked==False:
                self.request_slot(data)
   
    # Extract Appointment ID
    def get_appointment(self,data):
            response = self.session.get('https://cdn-api.co-vin.in/api/v2/appointment/beneficiaries').json()

            if not response.get('beneficiaries',[]):
                print("No user added in beneficiaries")
                exit()
            # print(json.dumps(response, indent=3))
            for user in response.get('beneficiaries'):
                ref_id = user.get("beneficiary_reference_id")
                if ref_id in self.user_id and user.get("appointments")!=[]:
                    for appointments in user.get('appointments'):
                        if appointments.get(f'appointment_id') and appointments.get(f'dose')==data["DoseType"]:
                            return appointments.get("appointment_id")
                    else:
                        print(f"User don't have ant active booking for dose{data['DoseType']}")
                else:
                    print("user don't have any active booking\n Exiting The application .......")
                    exit()

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
                print("Re-login Account : " + datetime.now().strftime("%H:%M:%S") + " 🤳")
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

                    center_name = center.get('name')
                    center_pin = center.get('pincode')
                    capacity = session.get('available_capacity')
                    session_date = session.get('date')
                    vaccine_name = session.get('vaccine')
                                        
                    if int(session.get('min_age_limit')) == self.age:
                        if capacity > int(data["MinimumVaccineAvailability"]):
                            MSG = f'💉 {capacity} #{vaccine_name} / {session_date} / {center_name} 📍{center_pin}'

                            # Send Notification via Termux:API App
                            print("Hurry Centers Available\n",MSG)
                        
                            BOOKED = self.book_slot()
                            if BOOKED:
                                print("Shutting Down CoWin Script 👩‍💻 ")
                                return True
                        else:
                            print(f"[info] Sorry {capacity} Vaccine Found found at {center_name} on {session_date}.")
                    else:
                        continue
        else:
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
            "appointment_id":self.appointment_id,
            "center_id":self.vacc_center ,
            "session_id":self.vacc_session,
            "beneficiaries":self.user_id,
            "slot":self.slot_time,
            "captcha": captcha,
            "dose": self.dose
            }

        response = self.session.post('https://cdn-api.co-vin.in/api/v2/appointment/reschedule',data=self.get_data())

        status =  response.status_code
        
        if status == 204:
            line_break()
            print("🏥 Appointment rescheduled successfully! 🥳 \n")
            # print(type(response))
            # print(json.dumps(response, indent=1))
            # result = response.json()
            # print(result)
            # appoint_ID = result.get("appointment_id")
            # print(f"Your Appointment ID is {appoint_ID}")
            # line_break()
            # with open(f"{self.mobile_no}_Booking_ID","a") as f:
            #     f.write(f"Your Appointment ID is {appoint_ID} booked on {datetime.datetime.now()}")
            return True
        elif status == 409:
            print("This vaccination center is completely booked for the selected date 😥")
            return False
        elif status == 401:
            self.login_cowin()
            self.book_slot()
        else:
            print("Error in Booking Slot")
            print(f'{status} : {response}')
            return False
    

if __name__ == '__main__':

    line_break()
    print("Welcome to CoWin Auto Slot rescheduling.....")
    line_break()
    cowin = CoWinBook()