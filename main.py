from tabulate import tabulate
import random
fac_sub={}
n=int(input('enter no of subject:'))
for i in range(n):
  print("_______________")
  print("subject",i+1, "info")
  sub=input("sub: ")
  list1=[]
  name=input("name")
  fac_sub[sub]=name
print(fac_sub)
cpd=int(input("enter no of classes per day:"))
timetable=[]
days=['monday', 'tues', 'wed', 'thur', 'fri', 'sat']
#inpuyt em classes ani subjects=list(fac_sub.keys())
day=0
tabl=['day']
i=0
for i in range(n):
  tabl.append(i+1)
print(tabl)
table=[[],[],[],[],[],[]]
subjects=list(fac_sub.values())
for i in range(n):
    tabl.append(i+1)
table=[[],[],[],[],[],[]]
table[0]=tabl
while(len(timetable)<6):
    timetable.append([])
    while(len(timetable[day])!=cpd):
        index=random.randint(0, len(subjects)-1)
        while(subjects[index] not in timetable[day]):
            timetable[day].append(subjects[index])
    day+=1
print(timetable)
j=0
dradict={}
for i in days:
  print(i)
  print(j)
  dradict[i]=timetable[j]
  j+=1
print(dradict)
  
a=list(dradict.keys())
b=list(dradict.values())
cname=['days']
d=[]
for i in range(cpd):
 cname.append((i+1))
for i in a:
  c=[]
  c.append(i)
  for i in dradict[i]:
    c.append(i)
  d.append(c)
print(d)
print(cname)
print(tabulate(d,headers=cname, tablefmt="grid"))
