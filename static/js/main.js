// Elements
const submitButton = document.getElementById('submit');
const submitText = document.getElementById('submitText');
const loadingIcon = document.getElementById('loadingIcon');
const errorDiv = document.getElementById('error');
const errorText = document.getElementById('errorText');
const queryInput = document.getElementById('query');
const charCount = document.getElementById('charCount');

const renderer = new marked.Renderer();
const originalListItem = renderer.listitem;

renderer.listitem = function (text) {
    if (text.includes('freshmart_source is a postgres source on the demo_sources cluster') ||
        text.includes('demo_sources is a 50cc managed cluster with replication factor 0') ||
        text.includes('sales is a subsource of freshmart_source')) {
        return `<li class="highlight-line">${text}</li>`;
    }
    return originalListItem.call(this, text);
};


marked.setOptions({
    renderer: renderer,
    breaks: true, // Adds <br> on single line breaks
    gfm: true, // GitHub Flavored Markdown
    headerIds: false // Prevents automatic header ID generation
});

queryInput.addEventListener('input', () => {
    charCount.textContent = `${queryInput.value.length} characters`;
});

async function makeApiCall(query, includeContext) {
    const response = await fetch('/api/basic', {
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

function formatDuration(seconds) {
    const wholeSeconds = Math.floor(seconds);
    const milliseconds = Math.round((seconds - wholeSeconds) * 1000);
    return `${wholeSeconds}s ${milliseconds}ms`;
}

submitButton.addEventListener('click', async () => {
    const query = queryInput.value.trim();
    if (!query) return;

    submitButton.disabled = true;
    submitText.textContent = 'Processing...';
    loadingIcon.classList.remove('hidden');
    errorDiv.classList.add('hidden');

    const mode = document.getElementById('mode').value;
    const includeContext = mode === 'on';

    try {
        const result = await makeApiCall(query, includeContext);
        console.log(result)

        const errorDiv = document.getElementById('error');
        const errorText = document.getElementById('errorText');

        errorDiv.classList.remove('hidden', 'bg-red-50', 'text-red-700');
        errorDiv.classList.add('bg-blue-50', 'text-blue-700');
        let timingText = `Inference Time: ${formatDuration(result.api_duration)}`;
        if (includeContext) {
            timingText += ` • Context Retrieval: ${formatDuration(result.context_duration)}`;
        }
        timingText += ` • End to End Duration: ${formatDuration(result.api_duration + result.context_duration)}`;

        errorText.textContent = timingText;
        errorDiv.style.display = 'block';

        let promptHtml = marked.parse(result.prompt || 'No prompt received');

        if (result.relevant_sources && result.relevant_sources.length > 0) {
            promptHtml += `\n\n### ${result.relevant_sources.length} Relevant Sources\n`;
            result.relevant_sources.forEach(source => {
                promptHtml += `- ${source.source_url}\n`;
            });
        }

        document.getElementById('prompt').innerHTML = marked.parse(promptHtml);

        document.getElementById('answer').innerHTML =
            marked.parse(result.answer || 'No answer received');
    } catch (err) {
        errorDiv.classList.remove('hidden', 'bg-blue-50', 'text-blue-700');
        errorDiv.classList.add('bg-red-50', 'text-red-700');
        errorText.textContent = `Error: ${err.message}`;
    } finally {
        submitButton.disabled = false;
        submitText.textContent = 'Submit Query';
        loadingIcon.classList.add('hidden');
    }
});

queryInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        submitButton.click();
    }
});
