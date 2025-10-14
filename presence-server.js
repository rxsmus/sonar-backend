
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

let onlineUsers = {};

io.on('connection', (socket) => {
  let username = null;

  socket.on('join', (name) => {
    username = name;
    onlineUsers[socket.id] = username;
    io.emit('online-users', Object.values(onlineUsers));
  });

  socket.on('disconnect', () => {
    delete onlineUsers[socket.id];
    io.emit('online-users', Object.values(onlineUsers));
  });
});

const PORT = process.env.PORT || 4000;
server.listen(PORT, () => {
  console.log(`Presence server running on port ${PORT}`);
});
