import requests
from fake_useragent import UserAgent
import hashlib
import json


class CoWinCancel():

    def line_break(self): 
        print("-"*25)
    def __init__(self,mobile_no):
        self.mobile_no = str(mobile_no)

        # All users data with active booking
        self.user_data = []

        # Request Session
        self.session =  requests.Session() 

        # Data for sending request
        self.data = {} 

        # Token Received from CoWIN
        self.bearerToken = None  # Session Token

      
        # Login and Save Token in file( filename same as mobile no)
        self.getSession()



    # Set Header in self.session = requests.Session()
    def set_headers(self):
        temp_user_agent = UserAgent()
        self.session.headers.update({
            'User-Agent': temp_user_agent.random,
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

    # Get Token saved in file for re-login and use
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
         
        print("OTP Sent 📲 ... \n")

        otp = input("Enter Otp Received on phone: ")

        return hashlib.sha256(otp.encode('utf-8')).hexdigest()

    # Show Registered Beneficiary Details
    def select_beneficiaries(self):

        response = self.session.get('https://cdn-api.co-vin.in/api/v2/appointment/beneficiaries').json()

        USERS = []

        if not response.get('beneficiaries',[]):
            print("No user added in beneficiaries")
            return
        # print(json.dumps(response, indent=3))
        counter = 1
        for user in response.get('beneficiaries'):
            for appointments in user.get('appointments'):
                if appointments.get(f'appointment_id'):
                    data = {
                            'index' : counter, 
                            'user_name' : f'{user.get("name")}',
                            'reference_id' : f'{user.get("beneficiary_reference_id")}',
                            'appointment_id' : f'{appointments.get("appointment_id")}',
                            'dose' : f'{appointments.get("dose")}',
                            'center':f'{appointments.get("name")}'
                            }
                    USERS.append(data)
                    counter +=1
         
        self.user_data = USERS
   
    # Cancel booking
    def canBookings(self):

        # To make post request of cancellation
        def reqCanBooking(app_id,ref_id):
            # print(app_id,ref_id)
            self.data = {
            "appointment_id": app_id,
            "beneficiariesToCancel":[ref_id]
            }
            data= self.get_data()
            response = self.session.post('https://cdn-api.co-vin.in/api/v2/appointment/cancel',data=data)
            status = response.status_code
            if status == 204:
                print("\n🏥 Appointment cancelled successfully! 🥳 ")
                self.user_data = []
                return True
            elif status == 409:
                print("\nAppointment cannot be cancelled!!!")
                return False

            elif status == 401:
                print("\nauthentication error")
                self.login_cowin()
                self.canBookings()
                return False  
            elif status == 400:
                print("\nBad Request")
                print(response)
                return False  

            else:
                print("\nError in Cancelling the Slot")
                print(f'{status} : ')
                return False

        if self.user_data:
            print(f"Select User for Cancellation 👩‍👦‍👦 \n")
            for user in self.user_data:
                print(f"{user['index']}: Press {user['index']} to cancel appointment of {user['user_name']} (dose-{user['dose']}) booked at - {user['center']}")
            self.line_break()
            print("Only one person allowed per instance")
            self.line_break()
            ans = int(input("Enter your responce here: "))

            for user_data in self.user_data:
                if user_data['index']== ans:
                    appoint_id = user_data['appointment_id']
                    refer_id = user_data['reference_id']

                    if reqCanBooking(appoint_id,refer_id):
                        return True
                    else:
                        pass
                break
            else:
                print("\nInvalid option!! Please try again....")
                self.canBookings()
        else:
            return -1

#  Driver Program
def main(mobile_no):
    newUser = CoWinCancel(mobile_no)
    newUser.select_beneficiaries()
    result = newUser.canBookings()
    if result == True:
        print("\n**********************************************************************\nDo you want to cancel more slot?")
        ans = input("Press Y to restart or press enter/return key to exit: ")
        if ans.lower()== 'y':
            main(mobile_no)
        else:
            pass
    elif result == -1:
        print("No active bookings found")


if __name__ == '__main__':
    mobile_no = input("Enter Your Mobile No: ")
    if len(mobile_no)==10:  
        main(mobile_no)
    else:
        print("Wrong Mobile Number")