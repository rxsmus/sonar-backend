const { Server } = require('socket.io');
const http = require('http');

const server = http.createServer();
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

const PORT = 4000;
server.listen(PORT, () => {
  console.log(`Presence server running on port ${PORT}`);
});
