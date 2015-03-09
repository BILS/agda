var test = 0
toggle_show_members = function(obj) {
	$(obj).closest('div.members').find('div.list').toggle();
    if (test++ % 2 == 0) {
        $(obj).text("Hide matching members")
    }
    else {
        $(obj).text("Show matching members")
    }
};
