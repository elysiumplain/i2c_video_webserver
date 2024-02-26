$(function() {
	$('a#save').on('click', function(e) {
		e.preventDefault()
		$.getJSON('/save',
			function(data) {
			//do nothing
			}
		);
		return false;
	});

	$('a#units').on('click', function(e) {
		e.preventDefault()
		$.getJSON('/units',
			function(data) {
				//do nothing
			}
		);
		return false;
	});

	$('a#colormap').on('click', function(e) {
		e.preventDefault()
		$.getJSON('/colormap',
			function(data) {
				//do nothing
			}
		);
		return false;
	});

	$('a#colormapback').on('click', function(e) {
		e.preventDefault()
		$.getJSON('/colormapback',
			function(data) {
				//do nothing
			}
		);
		return false;
	});

	$('a#filter').on('click', function(e) {
		e.preventDefault()
		$.getJSON('/filter',
			function(data) {
				//do nothing
			}
		);
		return false;
	});

	$('a#interpolation').on('click', function(e) {
		e.preventDefault()
		$.getJSON('/interpolation',
			function(data) {
				//do nothing
			}
		);
		return false;
	});

	$('a#interpolationback').on('click', function(e) {
		e.preventDefault()
		$.getJSON('/interpolationback',
			function(data) {
				//do nothing
			}
		);
		return false;
	});

	$('a#exit').on('click', function(e) {
		e.preventDefault()
		$.getJSON('/exit',
			function(data) {
				//do nothing
			}
		);
		return false;
	});
});
