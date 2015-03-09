$(document).ready(function() {
	var path = location.pathname.substring(1);
	if ( path ) {
		$('a[href$="' + path + '"]').addClass('current');
	}
});