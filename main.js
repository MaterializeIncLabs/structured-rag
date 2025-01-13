if (!API_KEY) {
    console.error(
        '\n🚫 Failed to load configuration\n' +
        'Cannot find API_KEY in config.js\n' +
        'Please check your configuration file.'
    );
    throw new Error('Missing API_KEY configuration');
}

const API_URL = 'https://api.kapa.ai/query/v1/projects/486796bb-793a-479b-afa5-9d8248eb6a51/chat/custom/';

// Elements
const submitButton = document.getElementById('submit');
const submitText = document.getElementById('submitText');
const loadingIcon = document.getElementById('loadingIcon');
const errorDiv = document.getElementById('error');
const errorText = document.getElementById('errorText');
const queryInput = document.getElementById('query');
const charCount = document.getElementById('charCount');

// Configure marked options
marked.setOptions({
    breaks: true, // Adds <br> on single line breaks
    gfm: true,    // GitHub Flavored Markdown
    headerIds: false // Prevents automatic header ID generation
});

// Update character count
queryInput.addEventListener('input', () => {
    charCount.textContent = `${queryInput.value.length} characters`;
});

async function makeApiCall(query, includeContext = false) {
    const messages = [];

    if (includeContext) {
        messages.push({
            role: "system",
            content: SYSTEM_PROMPT
        });
    }

    messages.push({
        role: "context",
    });

    if (includeContext) {
        messages.push({
            role: "user",
            content: "transactions is a Kafka avro upsert source. transactions is running on the sources cluster. the sources cluster is in status OOM-killed."
        });
    }

    messages.push({
        role: "query",
        content: query
    });

    const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
            'X-API-KEY': API_KEY,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            generation_model: "gpt-4o",
            messages: messages
        })
    });

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
}

// Copy to clipboard function
async function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    try {
        await navigator.clipboard.writeText(element.textContent);
        // You could add a toast notification here
        console.log('Copied to clipboard');
    } catch (err) {
        console.error('Failed to copy text: ', err);
    }
}

// Handle form submission
submitButton.addEventListener('click', async () => {
    const query = queryInput.value.trim();

    if (!query) return;

    submitButton.disabled = true;
    submitText.textContent = 'Processing...';
    loadingIcon.classList.remove('hidden');
    errorDiv.classList.add('hidden');

    try {
        const [ragResponse, structuredDataResponse] = await Promise.all([
            makeApiCall(query, false),
            makeApiCall(query, true)
        ]);

        // Convert markdown to HTML and display
        document.getElementById('ragResponse').innerHTML =
            marked.parse(ragResponse.answer || 'No answer received');
        document.getElementById('structuredResponse').innerHTML =
            marked.parse(structuredDataResponse.answer || 'No answer received');

    } catch (err) {
        errorDiv.textContent = `Error: ${err.message}`;
        errorDiv.classList.remove('hidden');
    } finally {
        submitButton.disabled = false;
        submitText.textContent = 'Submit Query';
        loadingIcon.classList.add('hidden');
    }
});

// Add keyboard shortcut for submission
queryInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        submitButton.click();
    }
});