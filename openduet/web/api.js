export async function api(path, body, method) {
  const options = {method: method || (body === undefined ? 'GET' : 'POST'), credentials: 'same-origin'};
  if (body !== undefined) {
    if (body instanceof Blob || body instanceof ArrayBuffer) options.body = body;
    else { options.body = JSON.stringify(body); options.headers = {'Content-Type': 'application/json'}; }
  }
  const response = await fetch(path, options);
  const value = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(typeof value.detail === 'string' ? value.detail : `Request failed (${response.status})`);
    error.status = response.status; throw error;
  }
  return value;
}
