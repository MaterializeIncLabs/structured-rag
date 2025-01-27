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
    const mode = document.getElementById('mode').value;
    const endpoint = mode === 'standard' ? '/api/basic' : '/api/custom';
    const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            query: query,
            include_context: includeContext
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
        errorDiv.classList.remove('hidden');
        errorText.textContent = `Error: ${err.message}`;
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
