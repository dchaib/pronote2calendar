import json

def read_config(config_file_path='config.json'):
    with open(config_file_path, 'r') as file:
        return json.load(file)

def update_pronote_password(new_password: str, config_file_path='config.json'):
    with open(config_file_path, 'r') as file:
        config = json.load(file)

    config['pronote']['password'] = new_password

    with open(config_file_path, 'w') as file:
        json.dump(config, file, indent=4)

    return config