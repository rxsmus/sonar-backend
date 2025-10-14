
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

// Dynamic namespaces for /lobby/:trackId
io.of(/^\/lobby\/.+$/).on('connection', (socket) => {
  const nsp = socket.nsp;
  // Each namespace manages its own online users
  if (!nsp.onlineUsers) nsp.onlineUsers = {};
  let username = null;
  let songId = nsp.name.split('/').pop();

  socket.on('join', (payload) => {
    username = payload.username;
    nsp.onlineUsers[socket.id] = { username };
    broadcastUsers(nsp);
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
