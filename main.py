import random

fac_sub = {}
n = int(input('Enter number of subjects: '))
for i in range(n):
    print("_______________")
    print("Subject", i + 1, "info")
    sub = input("Subject name: ")
    name = input("Faculty name: ")
    fac_sub[sub] = name  # Store subject and corresponding faculty

cpd = int(input("Enter number of classes per day: "))
days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
subjects = list(fac_sub.keys())  # Extract subject names (keys) for timetable

# Generate timetable
timetable = []
for _ in range(6):
    daily = []
    while len(daily) < cpd:
        subject = random.choice(subjects)
        if subject not in daily:
            daily.append(subject)
    timetable.append(daily)

# Map timetable to days
day_subject_map = dict(zip(days, timetable))


header = ['Day'] + [f'Class {i+1}' for i in range(cpd)]


col_width = 15  # Adjust as needed
print("-" * (col_width * (cpd + 1)))
print("".join(h.ljust(col_width) for h in header))
print("-" * (col_width * (cpd + 1)))


for day in days:
    row = [day] + day_subject_map[day]
    print("".join(str(item).ljust(col_width) for item in row))
print("-" * (col_width * (cpd + 1)))
