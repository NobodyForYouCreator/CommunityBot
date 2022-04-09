<h1 align="center">CommunityBot</h1>

Discord Bot was made for community servers. There aren't that much functions yet, but it'll grow rapidly and strongly. I hope it'll be nice project to view and to follow. Every update is being checked by me and there're very slight chances to find bug. In case of bug - connect me - NobodyForYou#3648

Python 3.11 recommended
## Installation

```bash
py -m venv .venv #Recommended to create environment
.venv\Scripts\activate #activate environment
pip install -U -r requirements.txt #install libraries
setx TOKEN <bot-token> #bot token instead <bot-token>
setx MONGOTOKEN <mongo-token> #mongo token instead <mongo-token>
```

## Launch

```bash
.venv\Scripts\activate #activate environment
py -m CommunityBot #Woah! Bot's working
```

## End it correctly!!!

```bash
Ctrl+C
```

## Data storage
```
#MongoDB
{
    "_id": <guild-id>,
    "modules": {},
    "users": {},
}
```
