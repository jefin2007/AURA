from brain.database import save_memory, get_memory


def set_name(name):
    save_memory("user_name", name, category="profile")


def get_name():
    return get_memory("user_name")


def set_age(age):
    save_memory("user_age", age, category="profile")


def get_age():
    return get_memory("user_age")


def set_location(location):
    save_memory("user_location", location, category="profile")


def get_location():
    return get_memory("user_location")


def set_birthday(birthday):
    save_memory("user_birthday", birthday, category="profile")


def get_birthday():
    return get_memory("user_birthday")
