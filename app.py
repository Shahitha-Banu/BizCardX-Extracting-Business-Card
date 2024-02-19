from PIL import Image
import easyocr
import numpy as np
import pandas as pd
import re
import sqlite3
import streamlit as st
from streamlit_option_menu import option_menu

#Reading and extrcting the data from the image
def readImage(image_path):
  image = Image.open(image_path)
  image_arr= np.array(image)
  reader = easyocr.Reader(["en"])
  result = reader.readtext(image_arr, detail = 0)
  return image_arr, result

#Data stored in json format for saving in DB
def extractData(result):
  data = {
      "name" : [],
      "designation" : [],
      "companyName" : [],
      "address" : [],
      "pincode" : [],
      "phone" : [],
      "mailID": [],
      "webAddress" : []}

  data["name"].append(result[0])
  data ["designation"].append(result[1])

  for i in range(2,len(result)):
    # Checking for the phone number
    if result[i].startswith("+") or "-" in result[i]:
      num = result[i]
      if "-" in result[i]:
        num = num.replace("-","")
      if "+" in num:
        num = num.replace("+", "")
      data["phone"].append(num)

    #Checking for the e-mail address
    elif "@" in result[i] and ".com" in result[i]:
      data["mailID"].append(result[i].lower())

    #checking for the website address
    elif ("www" in result[i] or "WWW" in result[i]) or ("@" not in result[i] and ".com" in result[i]):
      data["webAddress"].append(result[i].lower())

    #Checking for the Company Name
    elif re.match(r'^[a-zA-Z]', result[i]) and re.findall("[a-zA-Z]\Z", result[i]) :
      data["companyName"].append(result[i])

    #Checking for the address
    elif (re.match(r"^[0-9]", result[i]) and len(result[i]) > 6) or "," in result[i]:
      data["address"].append(result[i])

    #Checking the pincode
    elif result[i].startswith("Tamil") or result[i].isdigit():
      code = result[i]
      state = ""
      pin = ""
      for j in code:
        if j.isalpha():
          state += j
        elif j.isdigit():
          pin += j
      data["pincode"].append(pin)

  if state != "":
    data['address'].append(state)

  webLength = len(data["webAddress"])
  if webLength > 1:
    web = ""
    for i in data["webAddress"]:
      web = web + i
      if "." not in web:
        web += "."
    data["webAddress"].clear()
    data["webAddress"].append(web)
  web = data["webAddress"][0]
  if "www." not in web or " " in web:
    web = web.replace("www", "www.")
    web = web.replace(" ","")
    data["webAddress"].clear()
    data["webAddress"].append(web)
  if ".com" not in web:
    web = web.replace("com", ".com")
    data["webAddress"].clear()
    data["webAddress"].append(web)

  cNameLen = len(data["companyName"])
  if cNameLen > 1:
    cName = " ".join(data["companyName"])
    data["companyName"].clear()
    data["companyName"].append(cName)

  address = " ".join(data["address"])
  address = re.sub(r"[,;]","",address)
  if "Erode St " in address:
    address = address.replace("Erode St ", "St Erode")
  data["address"].clear()
  data["address"].append(address)

  phonelen = len(data["phone"])
  if phonelen > 1:
    ph = " ".join(data["phone"])
    data["phone"].clear()
    data["phone"].append(ph)
  return data

#creating Table using sqlite3
def createTable():
  createQuery = """CREATE TABLE IF NOT EXISTS cardDetails(
                                        name varchar(30),
                                        designation varchar(30),
                                        companyName varchar(30),
                                        address text,
                                        pincode varchar(10),
                                        phone varchar(30),
                                        mailID text,
                                        webAddress text)"""
  sqliteConnection.execute(createQuery)

#Inserting the details into the table
def insertRow(cardDF):
  for index,row in cardDF.iterrows():
    insertQuery = """ INSERT INTO cardDetails(name, designation,
                                    companyName, address,
                                    pincode, phone,
                                    mailID, webAddress) VALUES (?,?,?,?,?,?,?,?)"""
    values =(row['name'],
             row['designation'],
             row['companyName'],
             row['address'],
             row['pincode'],
             row['phone'],
             row['mailID'], 
             row['webAddress'])
    sqliteConnection.execute(insertQuery,values)
    sqliteConnection.commit()
    
#Reading and extracting the data from the image
def collectData(img):
    image = Image.open(img)
    image_arr, result = readImage(img)
    exData = extractData(result)
    createTable()
    cardDF = pd.DataFrame(exData)
    return image_arr, cardDF

def fetchTable():
  try:
    cursor.execute('SELECT * FROM cardDetails')
  except:
    st.warning("Kindly add the records to view the information!!")
  card = cursor.fetchall()
  sqliteConnection.commit()
  df= pd.DataFrame(card, columns= ["NAME","DESIGNATION","COMPANY_NAME","ADDRESS",
                                      "PINCODE","CONTACT","EMAIL","WEBSITE"])  
  return df
 
#streamlit Design Part
st.set_page_config(page_title= "BizCard Extraction",
                   layout= "wide",
                   initial_sidebar_state= "expanded")
st.header(":rainbow[BizCardX: Extracting Business Card Data with OCR]")
sqliteConnection = sqlite3.connect('bizCard.db')
cursor = sqliteConnection.cursor()

# Option Menu Creation
selected = option_menu(None, ["About","Extract & Upload","Querying"], 
                       icons=["card-text","database-add","database-gear"],
                       default_index=0,
                       orientation="horizontal",
                       styles={"nav-link": {"font-size": "20px", "text-align": "centre", "margin": "2px", "--hover-color": "#FFFF00"},
                               "icon": {"font-size": "20px"},
                               "container" : {"max-width": "6000px"},
                               "nav-link-selected": {"background-color": "#449A00"}})
if selected == "About":
    st.markdown("## :green[**Technologies Used :**] Python, EasyOCR, Streamlit, SQL, Pandas")
    st.markdown("## :green[**Overview :**] In this streamlit web app we can upload an image of a business card and extract relevant information from it using EasyOCR. We are able to view, modify or delete the extracted data using this app. This app would also allow users to save the extracted information into a database along with the uploaded business card image. The database would be able to store multiple entries, each with its own business card image and extracted information.")
elif selected == "Extract & Upload":
    img = ""
    flag = 0
    img = st.file_uploader("Upload the Image", type= ["png", "jpg", "jpeg"], label_visibility= "hidden")
    if img != None:
      col3,col4,col5 = st.columns([1,5,1])
      with col4:
        if st.button(":green[Extract and Upload]"):
          image_arr, cardDF = collectData(img)            
          col1,col2,col3 = st.columns(3)
          with col1:
            st.image(image_arr, caption = "The selected image", width = 275)
          with col2:
            st.text_input("Name", value = cardDF["name"][0],disabled  = True)
            st.text_input("Designation", value = cardDF["designation"][0],disabled  = True)
            st.text_input("Company Name", value = cardDF["companyName"][0],disabled  = True)
            st.text_input("Address", value = cardDF["address"][0],disabled  = True)
          with col3:
            st.text_input("Pincode", value = cardDF["pincode"][0],disabled  = True)
            st.text_input("Contact Number", value = cardDF["phone"][0],disabled  = True)
            st.text_input("E-Mail Id", value = cardDF["mailID"][0],disabled  = True)
            st.text_input("Website", value = cardDF["webAddress"][0],disabled  = True)
            
          cursor.execute('SELECT * FROM cardDetails')
          card = cursor.fetchall()
          sqliteConnection.commit()
          if len(card) != 0:
            for i in range(len(card)):
              if cardDF["name"][0] != card[i][0] and cardDF['mailID'][0] != card[i][6]:
                flag = 0
              else:
                flag = 1
                st.warning("Details already added in the repository!!Changes can be made using Querying!!")
                break
            if flag != 1:
              insertRow(cardDF)
          else:
            insertRow(cardDF)
elif selected == "Querying":
  tab1,tab2,tab3 = st.tabs([":green[View Details]",":green[Altar Record]",":green[Delete Record]"])
  with tab1:
    df3 = fetchTable()
    st.dataframe(df3)
  with tab2:
    df4 = fetchTable()
    option = st.selectbox(":green[Want to modify the database!!]", options = df4["NAME"], index = None, placeholder="Select the name", key = "opt")
    if option != None:
      cursor.execute(f"SELECT * FROM cardDetails WHERE name = '{option}'")
      data1 = cursor.fetchall()
      sqliteConnection.commit()
      df6 = pd.DataFrame(data1, columns= ["NAME","DESIGNATION","COMPANY_NAME","ADDRESS",
                                        "PINCODE","CONTACT","EMAIL","WEBSITE"])
      col6, col7 = st.columns(2)
      with col6:
        designationNew = st.text_input("Designation",value = df6["DESIGNATION"][0], key = "t1")
        cNameNew = st.text_input("Company Name", value = df6["COMPANY_NAME"][0], key = "t2")
        addressNew = st.text_input("Address", value = df6["ADDRESS"][0], key = "t3")
      with col7:
        pincodeNew = st.text_input("Pincode", value = df6["PINCODE"][0], key = "t4")
        contactNew = st.text_input("Contact Number", value = df6["CONTACT"][0], key = "t5")
        websiteNew = st.text_input("Website", value = df6["WEBSITE"][0], key = "t6")
      altar = st.button("Update the Database")
      if altar:
        updateQuery = f"""UPDATE cardDetails SET designation = '{designationNew}', companyName = '{cNameNew}',
                        address = '{addressNew}', pincode = '{pincodeNew}', phone = '{contactNew}',
                        webAddress = '{websiteNew}' WHERE name = '{df6["NAME"][0]}' AND mailID = '{df6["EMAIL"][0]}'"""
        cursor.execute(updateQuery)
        sqliteConnection.commit()
        cursor.execute(f"SELECT * FROM cardDetails WHERE name = '{option}'")
        data2 = cursor.fetchall()
        sqliteConnection.commit()
        df7 = pd.DataFrame(data2, columns= ["NAME","DESIGNATION","COMPANY_NAME","ADDRESS",
                                        "PINCODE","CONTACT","EMAIL","WEBSITE"])        
        st.dataframe(df7)
  with tab3:
    df5 = fetchTable()
    option1 = st.selectbox(":green[Want to Delete the record from the database, Select the corresponding name and email ID !!]", options = df5["NAME"], index = None, placeholder="Select the name")
    option2 = st.selectbox("", options = df5["EMAIL"], index = None, placeholder="Select the mail ID")
    delete = st.button("Delete")
    if delete:
      if option1 != None and option2 != None:
        cursor.execute(f"DELETE FROM cardDetails WHERE name = '{option1}' AND mailID = '{option2}'")
        sqliteConnection.commit()
        df6 = fetchTable()
        st.dataframe(df6)
      else:
        st.warning("Select the correct options!!")
