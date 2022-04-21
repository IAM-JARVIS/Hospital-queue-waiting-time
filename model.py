#import libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pickle

#path = '/content/drive/MyDrive/BE Project/data_withStrigs.csv'
path = 'data.csv'
data = pd.read_csv(path)
#print(data)

#converting strings to integer
#x1 = data.iloc[:,4].values
#from sklearn.preprocessing import LabelEncoder
#le = LabelEncoder()
#x1 = le.fit_transform(x1)
#data['diseaseNum'] = x1
#print(data)

#storing data in dependent and independent variables
#x = data.iloc[:,[2,6]].values
x = data.iloc[:,[2,4]].values
y = data.iloc[:,5].values

#splitting data for test and train purpose
from sklearn.model_selection import train_test_split
x_train, x_test, y_train, y_test = train_test_split(x,y, test_size=0.2, random_state=0)

#import random forest regressor
from sklearn.ensemble import RandomForestRegressor
#create random forest object
RFreg = RandomForestRegressor(n_estimators = 500, random_state = 0)
#fit random forest data with training data represented as x_train and y_train
RFreg.fit(x_train,y_train)

#can also use to find accuracy
#print(RFreg.score(x_test, y_test))

#prediction
#time_pred = RFreg.predict([[20,0.1]])
#print("Time predicted is %d" %time_pred)

#saving model to disk
pickle.dump(RFreg, open('model.pkl', 'wb'))
#loading pickle to compare results
model = pickle.load(open('model.pkl','rb'))