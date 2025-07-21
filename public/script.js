const socket = io();

const localCameraRadio = document.getElementById('localCamera');
const ipCameraRadio = document.getElementById('ipCamera');
const localCameraSelectionDiv = document.getElementById('localCameraSelection');
const localCameraDropdown = document.getElementById('localCameraDropdown');
const ipCameraInputDiv = document.getElementById('ipCameraInput');
const ipCameraSourceInput = document.getElementById('ipCameraSourceInput');
const addCameraButton = document.getElementById('addCameraButton');
const cameraGrid = document.getElementById('cameraGrid');

let widgetCounter = 0; // To generate unique IDs for camera widgets

// Helper function to sanitize source names for use as HTML IDs
function sanitizeId(source) {
    return source.replace(/[^a-zA-Z0-9-_]/g, '-');
}

// Function to toggle input visibility
function toggleInputVisibility() {
    if (localCameraRadio.checked) {
        localCameraSelectionDiv.style.display = 'block';
        ipCameraInputDiv.style.display = 'none';
        // Request camera list only if socket is connected
        if (socket.connected) {
            socket.emit('get-local-cameras');
        }
    } else {
        localCameraSelectionDiv.style.display = 'none';
        ipCameraInputDiv.style.display = 'block';
    }
}

// Initial visibility setup on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    toggleInputVisibility();
});

// Request cameras when socket connects (ensures connection is ready)
socket.on('connect', () => {
    console.log('Socket connected.');
    if (localCameraRadio.checked) {
        socket.emit('get-local-cameras');
    }
});

// Event listeners for radio buttons
localCameraRadio.addEventListener('change', toggleInputVisibility);
ipCameraRadio.addEventListener('change', toggleInputVisibility);

addCameraButton.addEventListener('click', () => {
    let source;
    let cameraType;

    if (localCameraRadio.checked) {
        source = localCameraDropdown.value;
        cameraType = 'local';
    } else {
        source = ipCameraSourceInput.value.trim();
        cameraType = 'ip';
    }

    if (!source) {
        alert('Please select a camera or enter a URL.');
        return;
    }

    const widgetId = `camera-widget-${widgetCounter++}`;
    socket.emit('start-camera', { source: source, type: cameraType, widgetId: widgetId });

    // Create camera container immediately
    const cameraContainer = document.createElement('div');
    cameraContainer.className = 'camera-container';
    cameraContainer.id = widgetId;

    cameraContainer.innerHTML = `
        <div class="camera-header">
            <h2>Camera: ${source}</h2>
            <button class="remove-camera-btn" data-widget-id="${widgetId}" data-source="${source}">Remove</button>
        </div>
        <img src="" alt="Camera Feed" class="camera-feed">
    `;
    cameraGrid.appendChild(cameraContainer);

    // Add event listener for remove button
    cameraContainer.querySelector('.remove-camera-btn').addEventListener('click', (event) => {
        const widgetIdToRemove = event.target.dataset.widgetId;
        const sourceToStop = event.target.dataset.source; // Still need source for backend
        socket.emit('stop-camera', sourceToStop); // Backend stops the FFmpeg process for this source
        document.getElementById(widgetIdToRemove).remove();
    });

    ipCameraSourceInput.value = ''; // Clear IP input
});

socket.on('local-cameras-list', (cameras) => {
    console.log('Frontend received local cameras list:', cameras);
    localCameraDropdown.innerHTML = ''; // Clear previous options
    if (cameras.length === 0) {
        localCameraDropdown.innerHTML = '<option value="">No local cameras found</option>';
        addCameraButton.disabled = true; // Disable add button if no cameras
    } else {
        cameras.forEach(camera => {
            const option = document.createElement('option');
            option.value = camera;
            option.textContent = camera;
            localCameraDropdown.appendChild(option);
        });
        addCameraButton.disabled = false;
    }
});

socket.on('camera-started', (data) => {
    // This event is now primarily for backend confirmation, not UI creation
    console.log(`Camera ${data.source} started on server for widget ${data.widgetId || 'N/A'}.`);
});

socket.on('camera-feed', (data) => {
    const { source, frame, widgetId } = data;
    const imgElement = document.querySelector(`#${widgetId} .camera-feed`);
    if (imgElement) {
        imgElement.src = `data:image/jpeg;base64,${frame}`;
    }
});

socket.on('camera-stopped', (source) => {
    console.log(`Camera ${source} stopped on server.`);
    // The UI element is removed by the remove button click handler, not here.
    // This event is just for backend confirmation.
});

socket.on('camera-error', (data) => {
    const { source, message, widgetId } = data;
    console.error(`Camera ${source} error: ${message}`);
    alert(`Error with camera ${source}: ${message}`);
    // Remove the specific widget that encountered an error
    const cameraContainer = document.getElementById(widgetId);
    if (cameraContainer) {
        cameraContainer.remove();
    }
});
