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

	$('a#colormap-next').on('click', function(e) {
		e.preventDefault()
		$.getJSON('/colormap/next',
			function(data) {
				//do nothing
			}
		);
		return false;
	});

	$('a#colormap-prev').on('click', function(e) {
		e.preventDefault()
		$.getJSON('/colormap/next',
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

	$('a#interpolation-next').on('click', function(e) {
		e.preventDefault()
		$.getJSON('/interpolation/next',
			function(data) {
				//do nothing
			}
		);
		return false;
	});

	$('a#interpolation-prev').on('click', function(e) {
		e.preventDefault()
		$.getJSON('/interpolation/prev',
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
