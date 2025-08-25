# 🎮 PVP System for BoltAbacus

This document describes the implementation of the Player vs Player (PVP) system for BoltAbacus, including experience points, real-time game sessions, and competitive features.

## 🚀 Features Implemented

### Core PVP Features
- **Room Creation**: Students can create PVP rooms with customizable settings
- **Room Joining**: Students can join rooms using unique 6-character codes
- **Real-time Gameplay**: WebSocket-based real-time communication
- **Experience Points**: Students gain XP for winning PVP matches
- **Level System**: XP-based leveling system (100 XP per level)

### Game Mechanics
- **Configurable Settings**: Number of questions, time per question, max players
- **Ready System**: Players must mark themselves as ready before game starts
- **Real-time Scoring**: Live score updates during gameplay
- **Winner Determination**: Based on score and time taken
- **Experience Rewards**: 50 XP awarded to winners

## 🏗️ Architecture

### Backend Technologies
- **Django 4.2.5**: Main web framework
- **Django Channels 4.0.0**: WebSocket support for real-time communication
- **PostgreSQL**: Database for storing game data
- **Redis** (optional): For production WebSocket scaling

### Database Models

#### Core PVP Models
- `PVPRoom`: Stores room information and settings
- `PVPRoomPlayer`: Tracks players in each room
- `PVPGameSession`: Manages active game sessions
- `PVPPlayerAnswer`: Records player answers and scores
- `PVPGameResult`: Stores final game results

#### Experience & Gamification Models
- `UserExperience`: Tracks user XP and levels
- `UserStreak`: Daily activity streaks (future feature)
- `UserCoins`: Virtual currency system (future feature)
- `UserAchievement`: Achievement system (future feature)

## 📡 API Endpoints

### PVP Room Management
```
POST /createPVPRoom/
POST /joinPVPRoom/
POST /getPVPRoomDetails/
POST /getPVPGameResult/
```

### User Experience
```
POST /getUserExperience/
```

### WebSocket Endpoint
```
ws://localhost:8000/ws/pvp/{room_id}/
```

## 🎯 Game Flow

### 1. Room Creation
1. Student creates room with settings:
   - Max players (2-4)
   - Number of questions (5-20)
   - Time per question (15-60 seconds)
   - Level/Class/Topic selection
2. System generates unique 6-character room code
3. Creator automatically joins the room

### 2. Room Joining
1. Other students enter the room code
2. System validates room availability
3. Players join and see room details

### 3. Game Preparation
1. All players must mark themselves as "Ready"
2. Room creator can start game when all players are ready
3. 3-2-1 countdown begins

### 4. Gameplay
1. Questions appear one by one with timer
2. Players submit answers in real-time
3. Scores update immediately
4. System tracks correct answers and time taken

### 5. Game Completion
1. All questions completed
2. Winner determined by score (then time)
3. Experience points awarded to winner
4. Results displayed to all players

## 🛠️ Setup Instructions

### 1. Install Dependencies
```bash
cd "BoltAbacus Copy"
pip install -r requirements.txt
```

### 2. Run Setup Script
```bash
python setup_pvp.py
```

### 3. Start the Server
```bash
python manage.py runserver
```

### 4. Update Frontend Configuration
Update the frontend API URL to point to your local backend:
```javascript
// In frontend .env file
VITE_BACKEND_API_URL=http://localhost:8000
```

## 🔧 Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/boltabacusdb

# Redis (for production WebSocket scaling)
REDIS_URL=redis://localhost:6379
```

### Room Code Generation
- 6 characters: Uppercase letters + numbers
- Example: "ABC123", "XYZ789"
- Automatically checked for uniqueness

### Experience System
- **Level Calculation**: `level = (XP // 100) + 1`
- **XP to Next Level**: `100 - (XP % 100)`
- **Win Reward**: 50 XP
- **Future Features**: Streak bonuses, achievement rewards

## 🧪 Testing

### API Testing
```bash
# Create a room
curl -X POST http://localhost:8000/createPVPRoom/ \
  -H "AUTH-TOKEN: your_token" \
  -H "Content-Type: application/json" \
  -d '{"max_players": 2, "number_of_questions": 10, "time_per_question": 30}'

# Join a room
curl -X POST http://localhost:8000/joinPVPRoom/ \
  -H "AUTH-TOKEN: your_token" \
  -H "Content-Type: application/json" \
  -d '{"room_id": "ABC123"}'
```

### WebSocket Testing
```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/pvp/ABC123/');

// Join room
ws.send(JSON.stringify({
  type: 'join_room',
  user_id: 123
}));

// Mark ready
ws.send(JSON.stringify({
  type: 'player_ready',
  user_id: 123
}));
```

## 🔮 Future Enhancements

### Planned Features
1. **Streak System**: Daily login and activity streaks
2. **Coin System**: Virtual currency for rewards
3. **Achievements**: Unlockable achievements
4. **Tournaments**: Multi-round competitions
5. **Leaderboards**: Global and class rankings
6. **Spectator Mode**: Watch ongoing games
7. **Replay System**: Review past games

### Technical Improvements
1. **Redis Integration**: For production WebSocket scaling
2. **Rate Limiting**: Prevent abuse
3. **Analytics**: Game performance tracking
4. **Mobile Optimization**: Better mobile experience
5. **Offline Support**: Handle connection issues

## 🐛 Troubleshooting

### Common Issues

1. **WebSocket Connection Failed**
   - Check if Django Channels is installed
   - Verify ASGI configuration
   - Check firewall settings

2. **Database Migration Errors**
   - Run `python manage.py makemigrations`
   - Run `python manage.py migrate`
   - Check database connection

3. **Room Creation Fails**
   - Verify user is a student
   - Check authentication token
   - Ensure database is accessible

### Debug Mode
Enable debug logging in settings.py:
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review Django Channels documentation
3. Check the database logs
4. Verify WebSocket connections

---

**🎉 Happy Gaming!** The PVP system is now ready to provide an engaging competitive experience for BoltAbacus students.
