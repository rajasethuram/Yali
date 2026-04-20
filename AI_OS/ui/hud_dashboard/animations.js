// YALI AI Operating System - Animations and Effects

class YALIAnimations {
  constructor() {
    this.init();
  }

  init() {
    this.setupScrollAnimations();
    this.setupHoverEffects();
    this.setupLoadingAnimations();
    this.setupParticleEffects();
  }

  setupScrollAnimations() {
    // Intersection Observer for scroll animations
    const observerOptions = {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('animate-in');
        }
      });
    }, observerOptions);

    // Observe all major sections
    document.querySelectorAll('.metric-card, .pipeline-section, .input-section, .response-section, .logs-section').forEach(el => {
      observer.observe(el);
    });
  }

  setupHoverEffects() {
    // Add hover effects to interactive elements
    document.querySelectorAll('.metric-card, .control-btn, .submit-btn').forEach(el => {
      el.addEventListener('mouseenter', this.handleHoverEnter.bind(this));
      el.addEventListener('mouseleave', this.handleHoverLeave.bind(this));
    });
  }

  handleHoverEnter(event) {
    const element = event.currentTarget;

    // Add glow effect
    element.style.boxShadow = element.style.boxShadow.replace(/rgba\([^)]+\)/g, 'rgba(0, 212, 255, 0.4)');

    // Scale effect for cards
    if (element.classList.contains('metric-card')) {
      element.style.transform = 'translateY(-8px) scale(1.02)';
    }
  }

  handleHoverLeave(event) {
    const element = event.currentTarget;

    // Reset glow effect
    element.style.boxShadow = element.style.boxShadow.replace(/rgba\([^)]+\)/g, 'rgba(0, 0, 0, 0.2)');

    // Reset scale effect
    if (element.classList.contains('metric-card')) {
      element.style.transform = 'translateY(0) scale(1)';
    }
  }

  setupLoadingAnimations() {
    // Add loading animations to metrics that update
    const metrics = document.querySelectorAll('.metric-value');
    metrics.forEach(metric => {
      metric.addEventListener('DOMSubtreeModified', () => {
        this.animateMetricUpdate(metric);
      });
    });
  }

  animateMetricUpdate(element) {
    element.style.transform = 'scale(1.1)';
    element.style.color = '#00d4ff';

    setTimeout(() => {
      element.style.transform = 'scale(1)';
      element.style.color = '';
    }, 300);
  }

  setupParticleEffects() {
    // Create floating particles in the background
    this.createParticles();
  }

  createParticles() {
    const particleContainer = document.createElement('div');
    particleContainer.className = 'particle-container';
    document.body.appendChild(particleContainer);

    // Create 50 particles
    for (let i = 0; i < 50; i++) {
      const particle = document.createElement('div');
      particle.className = 'particle';
      particle.style.left = Math.random() * 100 + '%';
      particle.style.top = Math.random() * 100 + '%';
      particle.style.animationDelay = Math.random() * 20 + 's';
      particle.style.animationDuration = (Math.random() * 10 + 10) + 's';
      particleContainer.appendChild(particle);
    }
  }

  // Utility methods for animations
  fadeIn(element, duration = 500) {
    element.style.opacity = '0';
    element.style.display = 'block';

    const start = performance.now();

    const fade = (timestamp) => {
      const elapsed = timestamp - start;
      const progress = elapsed / duration;

      if (progress < 1) {
        element.style.opacity = progress;
        requestAnimationFrame(fade);
      } else {
        element.style.opacity = '1';
      }
    };

    requestAnimationFrame(fade);
  }

  slideIn(element, direction = 'up', duration = 500) {
    const directions = {
      up: 'translateY(20px)',
      down: 'translateY(-20px)',
      left: 'translateX(20px)',
      right: 'translateX(-20px)'
    };

    element.style.opacity = '0';
    element.style.transform = directions[direction];
    element.style.display = 'block';

    const start = performance.now();

    const slide = (timestamp) => {
      const elapsed = timestamp - start;
      const progress = elapsed / duration;

      if (progress < 1) {
        element.style.opacity = progress;
        element.style.transform = `translateY(${20 * (1 - progress)}px)`;
        requestAnimationFrame(slide);
      } else {
        element.style.opacity = '1';
        element.style.transform = 'translateY(0)';
      }
    };

    requestAnimationFrame(slide);
  }

  // Typing animation for text
  typeText(element, text, speed = 50) {
    let i = 0;
    element.textContent = '';

    const type = () => {
      if (i < text.length) {
        element.textContent += text.charAt(i);
        i++;
        setTimeout(type, speed);
      }
    };

    type();
  }

  // Pulse animation
  pulse(element, duration = 1000) {
    element.style.animation = `pulse ${duration}ms ease-in-out`;

    setTimeout(() => {
      element.style.animation = '';
    }, duration);
  }

  // Shake animation for errors
  shake(element) {
    element.style.animation = 'shake 0.5s ease-in-out';

    setTimeout(() => {
      element.style.animation = '';
    }, 500);
  }
}

// Add CSS animations
const animationStyles = `
/* Particle Effects */
.particle-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

.particle {
  position: absolute;
  width: 2px;
  height: 2px;
  background: rgba(0, 212, 255, 0.3);
  border-radius: 50%;
  animation: float linear infinite;
}

@keyframes float {
  0% {
    transform: translateY(100vh) rotate(0deg);
    opacity: 0;
  }
  10% {
    opacity: 1;
  }
  90% {
    opacity: 1;
  }
  100% {
    transform: translateY(-100vh) rotate(360deg);
    opacity: 0;
  }
}

/* Scroll Animations */
.metric-card, .pipeline-section, .input-section, .response-section, .logs-section {
  opacity: 0;
  transform: translateY(30px);
  transition: all 0.6s ease;
}

.metric-card.animate-in, .pipeline-section.animate-in, .input-section.animate-in,
.response-section.animate-in, .logs-section.animate-in {
  opacity: 1;
  transform: translateY(0);
}

/* Staggered animation delays */
.metric-card:nth-child(1) { transition-delay: 0.1s; }
.metric-card:nth-child(2) { transition-delay: 0.2s; }
.metric-card:nth-child(3) { transition-delay: 0.3s; }
.metric-card:nth-child(4) { transition-delay: 0.4s; }

/* Shake animation */
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-5px); }
  75% { transform: translateX(5px); }
}

/* Pulse animation */
@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

/* Task result animations */
.task-result {
  animation: slideInFromBottom 0.5s ease-out;
}

.task-step {
  animation: fadeInScale 0.3s ease-out;
  animation-fill-mode: both;
}

.task-step:nth-child(1) { animation-delay: 0.1s; }
.task-step:nth-child(2) { animation-delay: 0.2s; }
.task-step:nth-child(3) { animation-delay: 0.3s; }

@keyframes slideInFromBottom {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeInScale {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* Loading states */
.loading {
  position: relative;
  overflow: hidden;
}

.loading::after {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.1), transparent);
  animation: loading-shimmer 1.5s infinite;
}

@keyframes loading-shimmer {
  0% { left: -100%; }
  100% { left: 100%; }
}

/* Voice wave animation */
.wave-bar {
  animation: wave 1.5s ease-in-out infinite;
}

.wave-bar:nth-child(1) { animation-delay: 0s; }
.wave-bar:nth-child(2) { animation-delay: 0.1s; }
.wave-bar:nth-child(3) { animation-delay: 0.2s; }
.wave-bar:nth-child(4) { animation-delay: 0.3s; }
.wave-bar:nth-child(5) { animation-delay: 0.4s; }

@keyframes wave {
  0%, 100% { height: 10px; }
  25% { height: 30px; }
  50% { height: 50px; }
  75% { height: 25px; }
}

/* Status indicator pulse */
.status-dot {
  animation: status-pulse 2s infinite;
}

@keyframes status-pulse {
  0%, 100% {
    box-shadow: 0 0 10px rgba(16, 185, 129, 0.6);
  }
  50% {
    box-shadow: 0 0 20px rgba(16, 185, 129, 0.9);
  }
}

/* Button hover effects */
.control-btn:hover i {
  transform: scale(1.1);
  transition: transform 0.2s ease;
}

.submit-btn:hover i {
  transform: translateX(2px);
  transition: transform 0.2s ease;
}

/* Input focus effects */
#task-input:focus + #voice-btn {
  border-color: rgba(0, 212, 255, 0.3);
  color: #00d4ff;
}

/* Responsive animations */
@media (max-width: 768px) {
  .particle {
    display: none; /* Disable particles on mobile for performance */
  }
}
`;

// Add animation styles to head
const animationStyleSheet = document.createElement('style');
animationStyleSheet.textContent = animationStyles;
document.head.appendChild(animationStyleSheet);

// Initialize animations when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new YALIAnimations();
});
