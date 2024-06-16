import requests
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, ConversationHandler, CallbackContext, Filters
from constant import TOKEN, CHAT_ID, API_KEY
import logging
import re

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

ADDRESS_FROM, ADDRESS_TO, CONTACT_PHONE, PASSENGER_NAME, TIME, CALC_ADDRESS_FROM, CALC_ADDRESS_TO, TRANSFER_FROM, TRANSFER_TO = range(9)

def start(update: Update, context: CallbackContext) -> None:
    buttons = ["🚖 Order", "🚘 Transfers", "💴 Calculation of Cost"]
    keyboard = list([button] for button in buttons)
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text("<b>Welcome!</b>\n<b>Choose an option to start conversation</b> 🚕", reply_markup=reply_markup, parse_mode=ParseMode.HTML)

def order(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("<b>Let's start with the pickup address 👇.</b>\n<b>Please provide it in the format 'Street name 123, City, Contry'.</b>", parse_mode=ParseMode.HTML)
    return ADDRESS_FROM

def address_from(update: Update, context: CallbackContext) -> int:
    context.user_data['address_from'] = update.message.text
    update.message.reply_text("<b>Great!</b>\n<b>Now, please provide the destination address 👉 in the format 'Street name 123, City, Contry'.</b>", parse_mode=ParseMode.HTML)
    return ADDRESS_TO

def address_to(update: Update, context: CallbackContext) -> int:
    context.user_data['address_to'] = update.message.text
    update.message.reply_text("<b>Perfect!</b>\n<b>Now, share the contact phone number \U0001F4F1 in the format +38640333555 followed by at least 5 digits.</b>", parse_mode=ParseMode.HTML)
    return CONTACT_PHONE

def contact_phone(update: Update, context: CallbackContext) -> int:
    phone_number = update.message.text
    phone_pattern = r'^\+386|0\d{2}\d{6}|\d{8}$'  # Example pattern: +87727 followed by at least 5 digits
    
    if re.match(phone_pattern, phone_number):
        context.user_data['contact_phone'] = phone_number
        update.message.reply_text("<b>Got it!</b>\n<b>If you want to provide your name, feel free to do so.</b>\n<b>Otherwise, just type 'skip'.</b>", parse_mode=ParseMode.HTML)
        return PASSENGER_NAME
    else:
        update.message.reply_text("<b>Invalid phone number format.</b>\n<b>Please provide the contact phone number in the format +38640555777 followed by at least 5 digits.</b>", parse_mode=ParseMode.HTML)
        return CONTACT_PHONE

def passenger_name(update: Update, context: CallbackContext) -> int:
    user_name = update.message.text
    if user_name.lower() == 'skip':
        user_name = 'Not provided'
    context.user_data['passenger_name'] = user_name
    update.message.reply_text("<b>Lastly,</b>\n<b>Specify the time \U0001F55B you would like the taxi to arrive in the format HH:MM (24-hour format).</b>", parse_mode=ParseMode.HTML)
    return TIME

def time(update: Update, context: CallbackContext) -> int:
    time_input = update.message.text
    time_pattern = r'^[0-2][0-9]:[0-5][0-9]$'  # 24-hour format: HH:MM

    if re.match(time_pattern, time_input):
        context.user_data['time'] = time_input
        if all(key in context.user_data for key in ['address_from', 'address_to', 'contact_phone', 'time']):
            coords_a = get_coordinate(API_KEY, context.user_data['address_from'])
            coords_b = get_coordinate(API_KEY, context.user_data['address_to'])
            if coords_a and coords_b:
                distance, duration = get_distance(API_KEY, coords_a, coords_b)
                if distance is not None:
                    order_details = (f"Taxi Order Details:\nFrom: {context.user_data['address_from']}\n"
                                     f"To: {context.user_data['address_to']}\n"
                                     f"Contact Phone: {context.user_data['contact_phone']}\n"
                                     f"Passenger Name: {context.user_data['passenger_name']}\n"
                                     f"Time: {context.user_data['time']}\n"
                                     f"Distance: {distance:.2f} km\n"
                                     f"Estimated Travel Time: {duration:.2f} minutes")
                    context.bot.send_message(chat_id=CHAT_ID, text=order_details)
                    update.message.reply_text("<b>Taxi order placed successfully!</b>\n<b>For additional information please call to the support +386 69 944 923</b>", reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)
                    return ConversationHandler.END
                else:
                    update.message.reply_text("<b>Не удалось вычислить расстояние.</b>", parse_mode=ParseMode.HTML)
                    return ConversationHandler.END
            else:
                update.message.reply_text("<b>Не удалось получить координаты для одного из адресов.</b>", parse_mode=ParseMode.HTML)
                return ConversationHandler.END
        else:
            update.message.reply_text("<b>Not enough information to place the order.</b>\n<b>Please provide all required details.</b>", parse_mode=ParseMode.HTML)
            return ConversationHandler.END
    else:
        update.message.reply_text("<b>Invalid time format.</b>\n<b>Please specify the time in the format HH:MM (24-hour format).</b>", parse_mode=ParseMode.HTML)
        return TIME

def get_coordinate(API_KEY, address):
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{address}.json"
    params = {
        'access_token': API_KEY,
        'limit': 1  # Ограничить результат одним ответом
    }
    response = requests.get(url, params=params)
    try:
        data = response.json()
        if data['features']:
            coordinates = data['features'][0]['geometry']['coordinates']
            print(f"Координаты для '{address}': {coordinates}")
            return coordinates
        else:
            print(f"Не удалось получить координаты: {address}")
            return None
    except requests.exceptions.ConnectionError as error:
        print(f"Не удалось подключиться к серверу: {error}")
        return None

def get_distance(API_KEY, coords1, coords2):
    url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{coords1[0]},{coords1[1]};{coords2[0]},{coords2[1]}"
    params = {
        'access_token': API_KEY
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
        if 'routes' in data:
            if data['routes']:
                distance = data['routes'][0]['distance'] / 1000  # расстояние в км
                duration = data['routes'][0]['duration'] / 60  # продолжительность в минутах
                return distance, duration
            else:
                print("Не удалось вычислить расстояние")
                return None
        else:
            print(f"Ошибка в ответе API: {data}")
            return None
    except requests.exceptions.ConnectionError as error:
        print(f"Не удалось подключиться к серверу: {error}")
        return None

def calculate_cost(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("<b>Let's start with the pickup address.</b>\n<b>Please provide it in the format 'Street name 123'.</b>", parse_mode=ParseMode.HTML)
    return CALC_ADDRESS_FROM

def calc_address_from(update: Update, context: CallbackContext) -> int:
    context.user_data['calc_address_from'] = update.message.text
    update.message.reply_text("<b>Great!</b>\n<b>Now, please provide the destination address.</b>", parse_mode=ParseMode.HTML)
    return CALC_ADDRESS_TO

def calc_address_to(update: Update, context: CallbackContext) -> int:
    context.user_data['calc_address_to'] = update.message.text
    coords_a = get_coordinate(API_KEY, context.user_data['calc_address_from'])
    coords_b = get_coordinate(API_KEY, context.user_data['calc_address_to'])
    if coords_a and coords_b:
        distance, duration = get_distance(API_KEY, coords_a, coords_b)
        if distance is not None:
            cost = 1.95 + distance * 1.09
            update.message.reply_text(f"<b>The distance between</b>'<b>{context.user_data['calc_address_from']}</b>' <b>and</b> '<b>{context.user_data['calc_address_to']}</b>' <b>is</b> <b>{distance:.2f}</b> <b>km.</b>\n<b>Estimated cost of the trip:</b> <b>{cost:.2f}</b><b> €</b>", parse_mode=ParseMode.HTML)
            return ConversationHandler.END
        else:
            update.message.reply_text("<b>Не удалось вычислить расстояние.</b>", parse_mode=ParseMode.HTML)
            return ConversationHandler.END
    else:
        update.message.reply_text("<b>Не удалось получить координаты для одного из адресов.</b>", parse_mode=ParseMode.HTML)
        return ConversationHandler.END

def transfer(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("<b>Please provide the pickup address for the transfer.</b>\n<b>Format: 'Street name 123'.</b>", parse_mode=ParseMode.HTML)
    return TRANSFER_FROM

def transfer_from(update: Update, context: CallbackContext) -> int:
    context.user_data['transfer_from'] = update.message.text
    update.message.reply_text("<b>Great!</b>\n<b>Now, please provide the destination address.</b>", parse_mode=ParseMode.HTML)
    return TRANSFER_TO

def transfer_to(update: Update, context: CallbackContext) -> int:
    context.user_data['transfer_to'] = update.message.text
    coords_a = get_coordinate(API_KEY, context.user_data['transfer_from'])
    coords_b = get_coordinate(API_KEY, context.user_data['transfer_to'])
    if coords_a and coords_b:
        distance, duration = get_distance(API_KEY, coords_a, coords_b)
        if distance is not None:
            cost = distance * 1.09
            update.message.reply_text(f"<b>The distance between</b>'<b>{context.user_data['transfer_from']}</b>' <b>and</b> '<b>{context.user_data['transfer_to']}</b>' <b>is</b> <b>{distance:.2f}</b> <b>km.</b>\n<b>Estimated travel time:</b> <b>{duration:.2f}</b> <b>minutes.</b>\n<b>Estimated cost of the transfer:</b> <b>{cost:.2f}</b><b>€</b>", parse_mode=ParseMode.HTML)
            return ConversationHandler.END
        else:
            update.message.reply_text("<b>Не удалось вычислить расстояние.</b>", parse_mode=ParseMode.HTML)
            return ConversationHandler.END
    else:
        update.message.reply_text("<b>Не удалось получить координаты для одного из адресов.</b>", parse_mode=ParseMode.HTML)
        return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("<b>Order Canceled.</b>", reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)
    return ConversationHandler.END

def main() -> None:
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    start_handler = CommandHandler('start', start)
    cancel_handler = CommandHandler('cancel', cancel)

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^(🚖 Order)$'), order)],  # Update entry point to handle button text
        states={
            ADDRESS_FROM: [MessageHandler(Filters.text & ~Filters.command, address_from)],
            ADDRESS_TO: [MessageHandler(Filters.text & ~Filters.command, address_to)],
            CONTACT_PHONE: [MessageHandler(Filters.text & ~Filters.command, contact_phone)],
            PASSENGER_NAME: [MessageHandler(Filters.text & ~Filters.command, passenger_name)],
            TIME: [MessageHandler(Filters.text & ~Filters.command, time)]
        },
        fallbacks=[cancel_handler]
    )

    calc_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^(💴 Calculation of Cost)$'), calculate_cost)],  # Entry point for cost calculation
        states={
            CALC_ADDRESS_FROM: [MessageHandler(Filters.text & ~Filters.command, calc_address_from)],
            CALC_ADDRESS_TO: [MessageHandler(Filters.text & ~Filters.command, calc_address_to)]
        },
        fallbacks=[cancel_handler]
    )

    transfer_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^(🚘 Transfers)$'), transfer)],  # Entry point for transfer
        states={
            TRANSFER_FROM: [MessageHandler(Filters.text & ~Filters.command, transfer_from)],
            TRANSFER_TO: [MessageHandler(Filters.text & ~Filters.command, transfer_to)]
        },
        fallbacks=[cancel_handler]
    )

    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(calc_handler)
    dispatcher.add_handler(transfer_handler)

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()