
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



// Dynamic namespaces for /lobby/:trackId or /lobby/:artist
io.of(/^\/lobby\/.+$/).on('connection', (socket) => {
  const nsp = socket.nsp;
  // Each namespace manages its own online users and chat history
  if (!nsp.onlineUsers) nsp.onlineUsers = {};
  if (!nsp.chatHistory) nsp.chatHistory = [];
  let username = null;
  let songId = null;
  let artist = null;

  socket.on('join', (payload) => {
    username = payload.username;
    songId = payload.songId || null;
    artist = payload.artist || null;
    nsp.onlineUsers[socket.id] = { username, songId, artist };
    broadcastUsers(nsp);
    // Send chat history to the newly joined user
    socket.emit('chat-history', nsp.chatHistory);
  });

  socket.on('send-message', (msg) => {
    // msg: { user, message, timestamp, avatar }
    const chatMsg = {
      ...msg,
      id: Date.now() + '-' + Math.random().toString(36).slice(2, 8)
    };
    nsp.chatHistory.push(chatMsg);
    // Limit chat history to last 100 messages
    if (nsp.chatHistory.length > 100) nsp.chatHistory = nsp.chatHistory.slice(-100);
    nsp.emit('new-message', chatMsg);
  });

  socket.on('disconnect', () => {
    delete nsp.onlineUsers[socket.id];
    broadcastUsers(nsp);
  });
});

function broadcastUsers(nsp) {
  const users = Object.values(nsp.onlineUsers).map(u => u.username);
  Object.keys(nsp.onlineUsers).forEach(sid => {
    if (nsp.sockets.get(sid)) {
      nsp.sockets.get(sid).emit('online-users', users);
    }
  });
}

const PORT = process.env.PORT || 4000;
server.listen(PORT, () => {
  console.log(`Presence server running on port ${PORT}`);
});
