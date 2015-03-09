// Like .html(), but including the tag itself.
(function($) {
    $.fn.outerHTML = function() {
        return $('<div>').append( this.eq(0).clone()).html();
    };
})(jQuery)

resetValues = function(obj, valuetype) {
	valuetype = typeof(valuetype) != 'undefined' ? valuetype : 'default';
	setValue = function(index, element) {
		var tag = $('.' + valuetype, element)
		if (tag.length == 0 ) {
			return;
		}
		var value = tag.text();
		$(':text, :password, select, textarea', element).val(value);
		$(':checkbox, :radio', element).removeAttr('checked').removeAttr('selected');
		$(':checkbox[value="' + value + '"]', element).attr('checked', true);
		$(':radio[value="' + value + '"]', element).attr('selected', true);
		// Clear is the only choice for file inputs.
		$(':file', element).replaceWith($(':file', element).outerHTML());
		$(':file', element).closest('td').find(':checkbox').attr('checked', true);

        // For number fields
        obj = $(':input', element)
        if ( obj.attr('type') == 'number' ) {
            obj.val(value);
        }
	}
	obj = $(obj).closest('.editfield, .editform').find('.editvalue').each(setValue);
}
