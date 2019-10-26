class Lab:
    def __init__(self, name, assignment_type, parts, options):
        self.name = name
        self.type = assignment_type
        self.parts = parts
        self.options = options

    def __str__(self):
        return f"{self.name}"
    
    @classmethod
    def find(cls, assignment, text):
        name = assignment.name.lower()
        text = text.lower()

        return name.find(text) is not -1

class Student:
    def __init__(self, first_name, last_name, email, section, id):
        self.first_name = first_name
        self.last_name = last_name
        self.full_name = f"{first_name} {last_name}"
        self.email = email
        self.section = section
        self.id = id
    
    def __str__(self):
        return f"{self.full_name} - {self.email} - Section {self.section}"

    @classmethod
    def find(cls, student, text):
        first_name = student.first_name.lower()
        last_name = student.last_name.lower()
        full_name = student.full_name.lower()
        email = student.email.lower()
        text = text.lower()

        return first_name.find(text) is not -1 or last_name.find(text) is not -1 or \
               full_name.find(text) is not -1 or email.find(text) is not -1
