from utils import update_flow_state, send_base_message
from database import db
from flow_states import feedback_asked, verif_number, number_verified


def send_feedback_messages():
    users = db.maintenant.users.find({})
    for user in users:
        if 'flow_state' in user and user['flow_state'] != verif_number and user['flow_state'] != number_verified:
            if 'Batch' in user and user['Batch'] != 1 and user['Batch'] != 2:
                send_base_message(user, 'SMS20')
                update_collections_after_end_of_challenge(user)


def update_collections_after_end_of_challenge(user):
    update_flow_state(user, feedback_asked)

    user_results = db.maintenant.results.find({'user_id': user['_id']}).sort('date', -1)
    if user_results.count() == 0:
        return "1"
    last_challenge_results_id = user_results[0]['_id']

    db.maintenant.results.update_one({
        '_id': last_challenge_results_id},
        {'$set': {'state': 'done'}})


if __name__ == '__main__':
    print('Starting challenge feedback')
    send_feedback_messages()
