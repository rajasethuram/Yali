// YALI AI Operating System - Modern UI JavaScript

class YALIInterface {
  constructor() {
    this.ws = null;
    this.isListening = false;
    this.currentTask = null;
    this.init();
  }

  init() {
    this.connectWebSocket();
    this.setupEventListeners();
    this.initializeLucideIcons();
    this.updateSystemStatus('online');
  }

  connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('Connected to YALI WebSocket');
      this.updateConnectionStatus(true);
    };

    this.ws.onclose = () => {
      console.log('Disconnected from YALI WebSocket');
      this.updateConnectionStatus(false);
      // Attempt to reconnect after 5 seconds
      setTimeout(() => this.connectWebSocket(), 5000);
    };

    this.ws.onmessage = (event) => {
      this.handleWebSocketMessage(event);
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  handleWebSocketMessage(event) {
    try {
      const data = JSON.parse(event.data);
      this.updateUI(data);
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  }

  updateUI(data) {
    // Update system metrics
    if (data.cpu !== undefined) {
      this.updateMetric('cpu', `${data.cpu}%`);
    }
    if (data.mem !== undefined) {
      this.updateMetric('mem', `${data.mem}%`);
    }
    if (data.wake !== undefined) {
      this.updateMetric('wake-status', data.wake.toUpperCase());
    }
    if (data.agents !== undefined) {
      this.updateMetric('agents', data.agents);
    }

    // Update pipeline status
    if (data.pipeline) {
      this.updatePipelineStatus(data.pipeline);
    }

    // Handle task completion
    if (data.task && data.results) {
      this.displayTaskResult(data.task, data.results);
    }

    // Update logs
    if (data.log) {
      this.addLogEntry(data.log);
    }
  }

  updateMetric(id, value) {
    const element = document.getElementById(id);
    if (element) {
      element.textContent = value;

      // Add visual feedback for changes
      element.style.transform = 'scale(1.05)';
      setTimeout(() => {
        element.style.transform = 'scale(1)';
      }, 200);
    }
  }

  updatePipelineStatus(status) {
    // Reset all pipeline steps
    document.querySelectorAll('.pipeline-step').forEach(step => {
      step.classList.remove('active', 'completed');
    });

    // Update based on current status
    const statusMap = {
      'planning': ['planning'],
      'planned': ['planning', 'executing'],
      'executing': ['planning', 'executing'],
      'validating': ['planning', 'executing', 'validating'],
      'completed': ['planning', 'executing', 'validating', 'completed']
    };

    const activeSteps = statusMap[status.toLowerCase()] || [];
    activeSteps.forEach(stepName => {
      const stepElement = document.querySelector(`[data-step="${stepName}"]`);
      if (stepElement) {
        if (stepName === 'completed') {
          stepElement.classList.add('completed');
        } else {
          stepElement.classList.add('active');
        }
      }
    });
  }

  displayTaskResult(task, results) {
    const responseContent = document.getElementById('response-content');

    // Clear welcome message if it exists
    const welcomeMessage = responseContent.querySelector('.welcome-message');
    if (welcomeMessage) {
      welcomeMessage.remove();
    }

    // Create result display
    const resultDiv = document.createElement('div');
    resultDiv.className = 'task-result';

    const taskHeader = document.createElement('div');
    taskHeader.className = 'task-header';
    taskHeader.innerHTML = `
      <div class="task-icon">
        <i data-lucide="check-circle"></i>
      </div>
      <div class="task-info">
        <div class="task-title">${task}</div>
        <div class="task-status">Completed</div>
      </div>
    `;

    const taskDetails = document.createElement('div');
    taskDetails.className = 'task-details';

    results.forEach(result => {
      const stepDiv = document.createElement('div');
      stepDiv.className = `task-step ${result.ok ? 'success' : 'error'}`;
      stepDiv.innerHTML = `
        <div class="step-content">
          <div class="step-text">${result.step}</div>
          <div class="step-result">${result.result || 'No result'}</div>
        </div>
        <div class="step-status">
          <i data-lucide="${result.ok ? 'check' : 'x'}"></i>
        </div>
      `;
      taskDetails.appendChild(stepDiv);
    });

    resultDiv.appendChild(taskHeader);
    resultDiv.appendChild(taskDetails);

    // Clear previous results and add new one
    responseContent.innerHTML = '';
    responseContent.appendChild(resultDiv);

    // Re-initialize Lucide icons for new elements
    lucide.createIcons();

    // Scroll to top of response section
    responseContent.scrollTop = 0;
  }

  addLogEntry(logText) {
    const logsElement = document.getElementById('logs');
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = `[${timestamp}] ${logText}\n`;

    logsElement.textContent = logEntry + logsElement.textContent;

    // Limit log entries to prevent memory issues
    const lines = logsElement.textContent.split('\n');
    if (lines.length > 100) {
      logsElement.textContent = lines.slice(0, 100).join('\n');
    }

    // Auto-scroll to bottom
    logsElement.scrollTop = logsElement.scrollHeight;
  }

  setupEventListeners() {
    // Task submission
    const submitBtn = document.getElementById('submit-btn');
    const taskInput = document.getElementById('task-input');

    submitBtn.addEventListener('click', () => this.submitTask());
    taskInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        this.submitTask();
      }
    });

    // Voice input
    const voiceBtn = document.getElementById('voice-btn');
    voiceBtn.addEventListener('click', () => this.toggleVoiceInput());

    // Settings
    const settingsBtn = document.getElementById('settings-btn');
    settingsBtn.addEventListener('click', () => this.showSettings());

    // Voice toggle in header
    const voiceToggle = document.getElementById('voice-toggle');
    voiceToggle.addEventListener('click', () => this.toggleVoiceInput());
  }

  async submitTask() {
    const taskInput = document.getElementById('task-input');
    const task = taskInput.value.trim();

    if (!task) {
      this.showNotification('Please enter a task', 'warning');
      return;
    }

    try {
      // Show loading state
      this.setLoadingState(true);

      const response = await fetch('/submit-task', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ task }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Task submitted:', data);

      // Clear input
      taskInput.value = '';

      // Show success feedback
      this.showNotification('Task submitted successfully!', 'success');

    } catch (error) {
      console.error('Submit failed:', error);
      this.showNotification('Failed to submit task. Please try again.', 'error');
    } finally {
      this.setLoadingState(false);
    }
  }

  toggleVoiceInput() {
    this.isListening = !this.isListening;
    const voiceOverlay = document.getElementById('voice-overlay');
    const voiceBtn = document.getElementById('voice-btn');

    if (this.isListening) {
      voiceOverlay.classList.add('active');
      voiceBtn.classList.add('listening');
      this.showNotification('Voice input activated', 'info');
      // In a real implementation, you would start voice recognition here
    } else {
      voiceOverlay.classList.remove('active');
      voiceBtn.classList.remove('listening');
      this.showNotification('Voice input deactivated', 'info');
    }
  }

  showSettings() {
    // Placeholder for settings panel
    this.showNotification('Settings panel coming soon!', 'info');
  }

  setLoadingState(loading) {
    const submitBtn = document.getElementById('submit-btn');
    const taskInput = document.getElementById('task-input');

    if (loading) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i data-lucide="loader"></i><span>Processing...</span>';
      taskInput.disabled = true;
    } else {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i data-lucide="send"></i><span>Execute</span>';
      taskInput.disabled = false;
    }

    lucide.createIcons();
  }

  showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
      <div class="notification-content">
        <i data-lucide="${this.getNotificationIcon(type)}"></i>
        <span>${message}</span>
      </div>
    `;

    // Add to page
    document.body.appendChild(notification);

    // Re-initialize icons
    lucide.createIcons();

    // Animate in
    setTimeout(() => notification.classList.add('show'), 10);

    // Remove after 3 seconds
    setTimeout(() => {
      notification.classList.remove('show');
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  }

  getNotificationIcon(type) {
    const icons = {
      'success': 'check-circle',
      'error': 'x-circle',
      'warning': 'alert-triangle',
      'info': 'info'
    };
    return icons[type] || 'info';
  }

  updateSystemStatus(status) {
    const statusDot = document.getElementById('system-status');
    const statusText = document.querySelector('.status-text');

    if (status === 'online') {
      statusDot.style.background = '#10b981';
      statusDot.style.boxShadow = '0 0 10px rgba(16, 185, 129, 0.6)';
      statusText.textContent = 'SYSTEM ONLINE';
      statusText.style.color = '#10b981';
    } else if (status === 'offline') {
      statusDot.style.background = '#ef4444';
      statusDot.style.boxShadow = '0 0 10px rgba(239, 68, 68, 0.6)';
      statusText.textContent = 'SYSTEM OFFLINE';
      statusText.style.color = '#ef4444';
    }
  }

  updateConnectionStatus(connected) {
    this.updateSystemStatus(connected ? 'online' : 'offline');
  }

  initializeLucideIcons() {
    // Initialize Lucide icons
    if (typeof lucide !== 'undefined') {
      lucide.createIcons();
    }
  }
}

// Initialize the interface when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new YALIInterface();
});

// Add notification styles dynamically
const notificationStyles = `
.notification {
  position: fixed;
  top: 20px;
  right: 20px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  padding: 16px 20px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  transform: translateX(100%);
  transition: transform 0.3s ease;
  z-index: 1001;
  max-width: 400px;
}

.notification.show {
  transform: translateX(0);
}

.notification-content {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #1f2937;
}

.notification-content i {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.notification-success .notification-content i { color: #10b981; }
.notification-error .notification-content i { color: #ef4444; }
.notification-warning .notification-content i { color: #f59e0b; }
.notification-info .notification-content i { color: #3b82f6; }
`;

// Add styles to head
const styleSheet = document.createElement('style');
styleSheet.textContent = notificationStyles;
document.head.appendChild(styleSheet);

