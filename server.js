const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const { spawn } = require('child_process');

const app = express();
const server = http.createServer(app);
const io = socketIo(server);

const PORT = process.env.PORT || 12467;

// Serve static files from the 'public' directory
app.use(express.static('public'));

// Stores FFmpeg child processes and associated widget IDs
// Structure: { source: { ffmpegProcess: ChildProcess, widgetIds: Set<string> } }
let cameraStreams = {}; 

io.on('connection', (socket) => {
    console.log('A user connected');

    socket.on('get-local-cameras', () => {
        console.log('Received request for local cameras.');
        const ffmpeg = spawn('ffmpeg', ['-list_devices', 'true', '-f', 'dshow', '-i', 'dummy']);
        let errorOutput = '';
        ffmpeg.stderr.on('data', (data) => {
            errorOutput += data.toString();
        });
        ffmpeg.on('close', (code) => {
            console.log('FFmpeg -list_devices process closed. Exit code:', code);
            console.log('FFmpeg -list_devices stderr output:\n', errorOutput);
            const cameraNames = [];
            const deviceRegex = /"([^"]+)"\s+\((video|none)\)/g;
            let match;
            while ((match = deviceRegex.exec(errorOutput)) !== null) {
                cameraNames.push(match[1]);
            }
            console.log('Detected camera names:', cameraNames);
            socket.emit('local-cameras-list', cameraNames);
        });
        ffmpeg.on('error', (err) => {
            console.error('Failed to spawn FFmpeg for listing cameras:', err.message);
            socket.emit('local-cameras-list', []); // Send empty list on error
        });
    });

    socket.on('start-camera', ({ source, type, widgetId }) => {
        console.log(`Attempting to start camera: ${source} (Type: ${type}) for widget: ${widgetId}`);

        // If the FFmpeg process for this source is not already running, start it
        if (!cameraStreams[source]) {
            let ffmpegArgs = [];

            if (type === 'local') {
                ffmpegArgs = [
                    '-f', 'dshow',
                    '-i', `video=${source}`,
                    '-f', 'image2pipe',
                    '-codec:v', 'mjpeg',
                    '-q:v', '3',
                    '-s', '640x480',
                    '-r', '15',
                    '-' // Output to stdout
                ];
            } else if (type === 'ip') {
                ffmpegArgs = [
                    '-i', source,
                    '-f', 'image2pipe',
                    '-codec:v', 'mjpeg',
                    '-q:v', '3',
                    '-s', '640x480',
                    '-r', '15',
                    '-' // Output to stdout
                ];
            } else {
                console.error(`Unknown camera type: ${type}`);
                socket.emit('camera-error', { source: source, message: `Unknown camera type: ${type}`, widgetId: widgetId });
                return;
            }

            const ffmpeg = spawn('ffmpeg', ffmpegArgs);

            ffmpeg.stdout.on('data', (data) => {
                // Emit to all connected widgets displaying this source
                if (cameraStreams[source] && cameraStreams[source].widgetIds) {
                    cameraStreams[source].widgetIds.forEach(id => {
                        io.to(socket.id).emit('camera-feed', { source: source, frame: data.toString('base64'), widgetId: id });
                    });
                }
            });

            ffmpeg.stderr.on('data', (data) => {
                console.error(`FFmpeg stderr for ${source}: ${data.toString()}`);
            });

            ffmpeg.on('close', (code) => {
                console.log(`FFmpeg process for ${source} exited with code ${code}`);
                // Notify all widgets using this source that it stopped
                if (cameraStreams[source] && cameraStreams[source].widgetIds) {
                    cameraStreams[source].widgetIds.forEach(id => {
                        io.to(socket.id).emit('camera-error', { source: source, message: `Stream closed (code: ${code})`, widgetId: id });
                    });
                }
                delete cameraStreams[source];
            });

            ffmpeg.on('error', (err) => {
                console.error(`Failed to start FFmpeg for ${source}: ${err.message}`);
                // Notify all widgets using this source about the error
                if (cameraStreams[source] && cameraStreams[source].widgetIds) {
                    cameraStreams[source].widgetIds.forEach(id => {
                        io.to(socket.id).emit('camera-error', { source: source, message: err.message, widgetId: id });
                    });
                }
                delete cameraStreams[source];
            });

            cameraStreams[source] = { ffmpegProcess: ffmpeg, widgetIds: new Set() };
        }
        // Add the widgetId to the set for this source
        cameraStreams[source].widgetIds.add(widgetId);
        socket.emit('camera-started', { source: source, widgetId: widgetId });
    });

    socket.on('stop-camera', (data) => {
        const { source, widgetId } = data;
        if (cameraStreams[source]) {
            console.log(`Stopping widget ${widgetId} for camera: ${source}`);
            cameraStreams[source].widgetIds.delete(widgetId);

            // If no more widgets are using this source, stop the FFmpeg process
            if (cameraStreams[source].widgetIds.size === 0) {
                console.log(`No more widgets using ${source}. Stopping FFmpeg process.`);
                cameraStreams[source].ffmpegProcess.kill('SIGKILL');
                delete cameraStreams[source];
                io.emit('camera-stopped', source); // Inform all clients that the source is fully stopped
            }
        }
    });

    socket.on('disconnect', () => {
        console.log('User disconnected');
        // When a user disconnects, remove their widgets from the active streams
        // This is a simplified approach; a more robust solution might track sockets per widget
        for (const source in cameraStreams) {
            if (cameraStreams[source].widgetIds) {
                // Iterate over a copy of the set to allow modification during iteration
                new Set(cameraStreams[source].widgetIds).forEach(widgetId => {
                    // Assuming widgetId is unique per client session or can be mapped back to a socket
                    // For simplicity, we'll just remove all widgets associated with this socket
                    // This part needs refinement if multiple clients can view the same widget
                    // For now, we'll just stop all streams if the server detects a disconnect
                    // This is a temporary measure, a proper solution would involve tracking socket.id per widget
                });
            }
        }
        // For now, we'll just stop all streams if the server detects a disconnect
        // This is a temporary measure, a proper solution would involve tracking socket.id per widget
        // and only stopping streams when no active sockets are listening to them.
        // For now, we'll leave streams running unless explicitly stopped by the user.
    });
});

server.listen(PORT, () => {
    console.log(`Server listening on port ${PORT}`);
});