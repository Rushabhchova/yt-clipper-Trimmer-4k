document.addEventListener('DOMContentLoaded', function() {
    const button = document.getElementById('clickMe');
    const message = document.getElementById('message');

    button.addEventListener('click', async function() {
        try {
            const response = await fetch('/api/hello');
            const data = await response.json();
            message.textContent = data.message;
            message.style.background = '#e8f5e9';
            message.style.border = '2px solid #4caf50';
        } catch (error) {
            message.textContent = 'Error: ' + error.message;
            message.style.background = '#ffebee';
            message.style.border = '2px solid #f44336';
        }
    });
});
