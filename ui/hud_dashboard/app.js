const ws = new WebSocket(`ws://${location.host}/ws`);
ws.onmessage = (ev)=>{
  const data = JSON.parse(ev.data);
  if(data.wake) document.getElementById('wake-status').innerText = `Wake: ${data.wake}`
  if(data.cpu) document.getElementById('cpu').innerText = `CPU: ${data.cpu}%`
  if(data.mem) document.getElementById('mem').innerText = `MEM: ${data.mem}%`
  if(data.agents) document.getElementById('agents').innerText = `Agents: ${data.agents}`
  if(data.pipeline) document.getElementById('pipeline').innerText = `Pipeline: ${data.pipeline}`
  if(data.log){
    const l = document.getElementById('logs');
    l.innerText = data.log + '\n' + l.innerText;
  }
}

// Handle task submission
document.getElementById('submit-btn').addEventListener('click', async ()=>{
  const input = document.getElementById('task-input');
  const task = input.value.trim();
  if(!task) return;
  
  try{
    const res = await fetch('/submit-task', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({task})
    });
    const data = await res.json();
    console.log('Task submitted:', data);
    input.value = '';
  }catch(e){
    console.error('Submit failed:', e);
  }
});

// Allow Enter key to submit
document.getElementById('task-input').addEventListener('keypress', (e)=>{
  if(e.key === 'Enter') document.getElementById('submit-btn').click();
});

