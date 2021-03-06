import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pymongo import UpdateOne, InsertOne
from utils import update_flow_state, send_message
from database import db
from flow_states import verif_number
from datetime import datetime

def get_spreadsheet_data(spreadsheet):
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('Maintenant-co-18e27771f6d8.json', scope)
    gc = gspread.authorize(credentials)
    wks = gc.open(spreadsheet).sheet1

    data = wks.get_all_records()
    return data


def update_collection(spreadsheet, collection):
    data = get_spreadsheet_data(spreadsheet)
    db.maintenant[collection].delete_many({})
    inserted_ids = db.maintenant[collection].insert_many(data).inserted_ids

    print('Succesfully inserted {} documents in {} from {}'.format(len(inserted_ids), collection, spreadsheet))


def update_all_collections():
    update_collection('Défis', 'challenges')
    update_collection('Messages de base', 'messages')


def new_users():
    # we should probably clean the phone number instead of the ugly thing we did in get_user
    collection = 'users'
    spreadsheet = 'inscrits_from_squarespace'
    users = list(db.maintenant.users.find({}))
    users_sub_date = [user['Submitted On'] for user in users]

    spreadsheet_users = get_spreadsheet_data('inscrits_from_squarespace')
    new_users_data = [user for user in spreadsheet_users if user['Submitted On'] not in users_sub_date]
    old_users_updated_data = [user for user in spreadsheet_users if user['Submitted On'] in users_sub_date]

    if len(new_users_data):
        inserted_ids = db.maintenant[collection].insert_many(new_users_data).inserted_ids
        print('Succesfully inserted {} documents in {} from {}'.format(len(inserted_ids), collection, spreadsheet))

    result = db.maintenant[collection].bulk_write([
        UpdateOne(filter={'Submitted On': user['Submitted On']},
                  update={'$set': user}) for user in old_users_updated_data])
    print('Succesfully updated {} documents in {} from {}'.format(result.modified_count, collection, spreadsheet))

    if len(new_users_data):
        for user in new_users_data:
            welcoming_committee(user['Tlphone'])


def welcoming_committee(tel):
    user = db.maintenant.users.find_one({'Tlphone': tel})
    if 'flow_state' in user:
        return "0"
    welcome_message = db.maintenant.messages.find_one({'sms_id': 'SMS1'})
    send_message(user, welcome_message['content'])

    update_flow_state(user, verif_number)


def update_firsts_batches():
    firsts_batches = list(db.maintenant['users'].find({'Batch': {'$ne': None}}))
    firsts_ids = [user['_id'] for user in firsts_batches]
    operations = [InsertOne({
        'user_id': user_id,
        'challenge_id': i+1,
        'relance': 1,
        'date': datetime.now(),
        'state': 'done'
    }) for user_id in firsts_ids for i in range(6)]
    # print(operations)
    result = db.maintenant['results'].bulk_write(operations)
    print(result.bulk_api_result)


if __name__ == '__main__':
    update_all_collections()
