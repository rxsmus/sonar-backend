
const express = require('express');
const app = express();
const http = require('http');
const { Server } = require('socket.io');

app.get('/', (req, res) => {
  res.send('Presence server is running');
});

const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: '*',
    methods: ['GET', 'POST']
  }
});

// onlineUsers: { socketId: { username, songId } }
let onlineUsers = {};

io.on('connection', (socket) => {
  let username = null;
  let songId = null;

  // Expect join payload: { username, songId }
  socket.on('join', (payload) => {
    username = payload.username;
    songId = payload.songId;
    onlineUsers[socket.id] = { username, songId };
    broadcastUsersForSong(songId);
  });

  socket.on('update-song', (newSongId) => {
    if (onlineUsers[socket.id]) {
      onlineUsers[socket.id].songId = newSongId;
      songId = newSongId;
      broadcastUsersForSong(songId);
    }
  });

  socket.on('disconnect', () => {
    delete onlineUsers[socket.id];
    if (songId) broadcastUsersForSong(songId);
  });
});

function broadcastUsersForSong(songId) {
  // Only users with the same songId
  const users = Object.values(onlineUsers)
    .filter(u => u.songId === songId)
    .map(u => u.username);
  // Send only to sockets with this songId
  Object.entries(onlineUsers).forEach(([sid, u]) => {
    if (u.songId === songId && io.sockets.sockets.get(sid)) {
      io.sockets.sockets.get(sid).emit('online-users', users);
    }
  });
}

const PORT = process.env.PORT || 4000;
server.listen(PORT, () => {
  console.log(`Presence server running on port ${PORT}`);
});
