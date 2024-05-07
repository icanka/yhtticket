
import regex
import logging
from typing import Dict
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
 
# Make a regular expression
# for validating an Email
reg = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
reg = r"^[\p{L}\u0020]+$"
# Define a function for
# for validating an Email
def check(email):
 
    # pass the regular expression
    # and the string into the fullmatch() method
    if(regex.fullmatch(reg, email)):
        print("Valid Email")
 
    else:
        print("Invalid Email")
 
# Driver Code
if __name__ == '__main__':
 
# states
    SELECTING_MAIN_ACTION, ADDING_PERSONAL_INFO, ADDING_CREDIT_CARD_INFO = range(0, 3)
    
    
    
    print(SELECTING_MAIN_ACTION)
    print(ADDING_PERSONAL_INFO)
    print(ADDING_CREDIT_CARD_INFO)
    print(ConversationHandler.END, end='\n')
    print()
    print(ConversationHandler.TIMEOUT)
    print(ConversationHandler.WAITING)
    