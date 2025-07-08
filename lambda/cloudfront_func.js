function handler(event) {
	var request = event.request;
	if (request.headers.host != null) {
    	var host = request.headers.host.value;
    	var uri = request.uri;
    	var newurl = `https://${host}/webtool/index.html`
      
    	if (uri == '/webtool/' || uri === '/') {
    		return {
    			statusCode: 302,
    			statusDescription: 'Found',
    			headers: { "location": { "value": newurl } }
    		};
    	}
	}
  
	return request;
}