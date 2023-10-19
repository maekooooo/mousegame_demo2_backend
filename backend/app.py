import random
import pymongo
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from mongodb.MongoConnector import MongoConnector


class GameApp:
    def __init__(self):
        self.app = Flask(__name__)
        CORS(self.app)
        self.mongo_connector = MongoConnector()
        self.configure_mongodb()
        self.configure_routes()
        return

    def configure_mongodb(self):
        self.mongo_connector.set_connection_string(
            username='test_user1',
            password='test_user',
            cluster_link='cluster0.o981put.mongodb.net'
        )
        self.mongo_connector.connect_client()
        db = self.mongo_connector.client['user_data']
        collection = db['__private']
        print(db.name, collection.name)
        return

    def configure_routes(self):
        self.app.route('/api/register', methods=['POST'])(self.register_user)
        self.app.route('/api/user/<username>', methods=['GET', 'POST'])(self.attempt_login)
        self.app.route('/api/user/<username>/profile', methods=['GET'])(self.get_account_data)
        self.app.route('/api/user/<username>/hunt', methods=['PUT'])(self.trigger_hunt)
        self.app.route('/api/user/<username>/delete', methods=['DELETE'])(self.delete_user_data)
        self.app.route('/api/global', methods=['GET'])(self.get_global_hunt)
        return

    def check_username_exists(self, username):
        users_list = self.mongo_connector.connect_table('user_data', '__private')
        existing_user = users_list.find_one({'username': username})
        if existing_user:
            print(f'Existing User: {username}')
            return True
        print(f'Non-exist: {username}')
        return False

    def attempt_login(self, username):
        data = request.get_json()
        allow_login = False

        exists = self.check_username_exists(data['username'])
        if exists:
            account = self._mongo_fetch_private(data['username'])
            if data['password'] == account['password']:
                allow_login = True
            pass

        if allow_login:
            user_profile = self.get_user_profile(data['username'])
            user_profile.pop('_id')
            user_last_hunt = self.get_user_last_hunt(data['username'])
            user_last_hunt.pop('_id')
            print(user_last_hunt)
            print(user_profile)
            return jsonify({'profile': user_profile, 'last_hunt': user_last_hunt})

        return jsonify({'error': 'User not found'}), 404

    def register_user(self):
        data = request.get_json()

        if 'username' not in data or 'password' not in data:
            return jsonify({'error': 'Missing username or password'}), 400

        self.mongo_connector.connect_table('user_data', '__private')

        exists = self.check_username_exists(data['username'])
        if exists:
            return jsonify({'error': 'Username already exists'}), 409

        new_account = {
            'username': data['username'],
            'password': data['password']
        }

        new_user_profile = {
            'username': data['username'],
            'gold': 0,
            'exp': 0,
            'hunt_count': 0
        }

        last_hunt_entry = {
            'username': data['username'],
            'timestamp': 0,
            'gold_gained': 0,
            'exp_gained': 0
        }

        user_accounts = self._mongo_connect_private()
        user_profiles = self._mongo_connect_user_data()
        last_hunts = self._mongo_connect_last_hunt()
        user_accounts.insert_one(new_account)
        user_profiles.insert_one(new_user_profile)
        last_hunts.insert_one(last_hunt_entry)

        return jsonify({'message': 'User registered successfully'}), 201

    def trigger_hunt(self, username):
        """
        When hunt is triggered, fetch user profile gold, exp, hunt
        then update with random values +5 to +20 for gold and exp, +1 for hunt count
        """
        data = request.get_json()
        self.update_user_profile(username, data['goldGained'], data['expGained'])
        self.update_user_last_hunt(username, datetime.now(), data['goldGained'], data['expGained'])

        return jsonify({'profile': data})

    def update_user_profile(self, username, gold, exp):
        user_profile = self._mongo_connect_user_data()
        profile_filter = {'username': username}
        update = {'$inc': {
            'gold': gold,
            'exp': exp,
            'hunt_count': 1
            }
        }
        result = user_profile.update_one(profile_filter, update)
        return

    def update_user_last_hunt(self, username, timestamp, gold_gained, exp_gained):
        last_hunt_data = {
            'username': username,
            'timestamp': timestamp,
            'gold_gained': gold_gained,
            'exp_gained': exp_gained
        }
        last_hunt = self._mongo_connect_last_hunt()

        hunts_history = self._mongo_connect_last_hunt()
        hunts_history.insert_one(last_hunt_data)
        return

    def get_account_data(self, username):
        exists = self.check_username_exists(username)
        if exists:
            user_profile = self.get_user_profile(username)
            user_last_hunt = self.get_user_last_hunt(username)
            user_profile.pop('_id')
            user_last_hunt.pop('_id')
            return jsonify({'user_profile': user_profile, 'user_last_hunt': user_last_hunt})
        return jsonify({'error': 'User not found'}), 404

    def get_global_hunt(self):
        global_hunt = self._mongo_connect_last_hunt()
        global_hunt_data = list(global_hunt.find({}).sort("timestamp", pymongo.DESCENDING).limit(5))

        for hunt in global_hunt_data:
            if '_id' in hunt:
                del hunt['_id']
        print(global_hunt_data)
        return jsonify(global_hunt_data)

    def get_user_profile(self, username):
        user_profile = self._mongo_fetch_user_profile(username)
        if not user_profile:
            return {}
        return user_profile

    def get_user_last_hunt(self, username):
        user_last_hunt = self._mongo_fetch_last_hunt(username)
        if not user_last_hunt:
            return {}
        return next(user_last_hunt)

    def delete_user_data(self, username):
        print(username)
        accounts = self._mongo_connect_private()
        user_data = self._mongo_connect_user_data()
        db_filter = {'username': username}

        exists = self.check_username_exists(username)
        if exists:
            accounts.delete_one(db_filter)
            user_data.delete_one(db_filter)

            user_check = accounts.find_one(db_filter)
            if user_check is None:
                print("Deleted account successfully")
                return jsonify({'result': 'Success deletion of account'})
            else:
                print("Failed to delete account")
                return jsonify({'error': 'Failed to delete account'}), 500
        else:
            print("User not found")
            return jsonify({'error': 'User not found'}), 404

    @staticmethod
    def generate_gold_exp_gained():
        gold_gained = random.randint(5, 20)
        exp_gained = random.randint(5, 20)
        return gold_gained, exp_gained

    def run(self):
        self.app.run(debug=True)
        return

    #region mongo functions
    def _mongo_connect_private(self):
        user_account = self.mongo_connector.connect_table('user_data', '__private')
        return user_account

    def _mongo_connect_user_data(self):
        user_data = self.mongo_connector.connect_table('user_data', 'user_data')
        return user_data

    def _mongo_connect_last_hunt(self):
        last_hunt = self.mongo_connector.connect_table('global_feed', 'hunts_history')
        return last_hunt

    def _mongo_fetch_private(self, username):
        user_data = self.mongo_connector.connect_table('user_data', '__private')
        return user_data.find_one({'username': username})

    def _mongo_fetch_user_profile(self, username):
        user_data = self.mongo_connector.connect_table('user_data', 'user_data')
        return user_data.find_one({'username': username})

    def _mongo_fetch_last_hunt(self, username):
        user_data = self.mongo_connector.connect_table('global_feed', 'hunts_history')
        return user_data.find({'username': username}).sort([('timestamp', -1)]).limit(1)

    def return_profile_username(self, username):
        profile = self._mongo_fetch_user_profile(username)
        return profile['username']

    def return_profile_gold(self, username):
        profile = self._mongo_fetch_user_profile(username)
        return profile['gold']

    def return_profile_exp(self, username):
        profile = self._mongo_fetch_user_profile(username)
        return profile['exp']

    def return_profile_hunt_count(self, username):
        profile = self._mongo_fetch_user_profile(username)
        return profile['hunt_count']

    def return_hunt_username(self, username):
        last_hunt = self._mongo_fetch_last_hunt(username)
        return last_hunt['username']

    def return_hunt_timestamp(self, username):
        last_hunt = self._mongo_fetch_last_hunt(username)
        return last_hunt['timestamp']

    def return_hunt_gold_gained(self, username):
        last_hunt = self._mongo_fetch_last_hunt(username)
        return last_hunt['gold_gained']

    def return_hunt_exp_gained(self, username):
        last_hunt = self._mongo_fetch_last_hunt(username)
        return last_hunt['exp_gained']

    #endregion


if __name__ == '__main__':
    game_app = GameApp()
    game_app.run()
