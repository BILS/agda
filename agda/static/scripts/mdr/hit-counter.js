format = function(template, args) {
	// Args are template, arg1, arg2, arg3...
	return template.replace(/{(\d+)}/g, function(match, number) {
		var arg = args[parseInt(number)];
		return typeof arg != 'undefined' ? arg : match;
	});
}

capitalize = function(str) {
	return str.charAt(0).toUpperCase() + str.substring(1);
}

pluralize = function(word, number) {
	if (typeof word == 'object') {
		if (word.length == 3) {
			return word[0] + (number == 1 ? word[1] : word[2]);
		}
		return number == 1 ? word[0] : word[1];
	}
	if (word.charAt(word.length - 1) == 'y') {
		return number == 1 ? word : word.substr(0, word.length - 1) + 'ies';
	}
	return number == 1 ? word : word + 's';
}

function repeat (str, num) {
	return Array(num + 1).join(str);
}

function HitCounter (element, msg, hits, labels) {
	this.done = false;
	this.element = element;
	this.hits = hits;
	this.msg = msg;
	this.labels = labels;
	this.updates = 0;
	
	this.update = function () {
		var hits = new Array();
		var sum = 0;
		for (var i = 0; i < this.hits.length; i = i + 1) {
			var n = $(this.hits[i]).length
			var label = pluralize(this.labels[i], n);
			hits.push(n + ' ' + label);
			sum = sum + n;
		}
		var msg = format(this.msg, hits);
		if (this.done) {
			$(this.element).html('Done. ' + capitalize(msg));
		} else {
			var i = 4;
			var throbber = repeat('.', this.updates % i) + ' ' + repeat('.', i - this.updates % i - 1);
			$(this.element).html('Searching' + throbber + ' ' + (sum ? msg : ''));
		}
		this.updates = this.updates + 1; 
	}
	

	this.auto_update = function (delay) {
		var obj = this;
		if (!delay) {
			delay = 500;
		}
		function callback () {
			obj.update();
			if (!obj.done) {
				window.setTimeout(callback, delay);
			}
		}
		callback();
		return this;
	}
	
	this.done_when_ready = function () {
		var obj = this;
		$(document).ready(function () { 
			obj.done = true; 
			obj.update(); });
		return this;
	}
	
	return this;
}

function countHits(element, hits, labels, display, messages, throbber) {
	var counts = [];
	for (var i = 0; i < hits.length; i++) 
		counts[i] = 0;
	var set = $(element).find(hits[hits.length - 1]);
	counts[counts.length - 1] = set.length;
	if (hits.length > 1) {
		for (var i = 0; i < set.length; i++) {
			var e = set[i];
			var _c = countHits(e, hits.slice(0, -1), labels.slice(0, -1), display.slice(0, -1), messages.slice(0, -1), throbber);
			for (var j = 0; j < _c.length; j++)
				counts[j] += _c[j];
		}
	}
	if (display[display.length - 1]) {
		var args = [throbber];
		for (var i = 0; i < counts.length; i++) {
			args.push(counts[i]);
			args.push(pluralize(labels[i], counts[i]));
		}
		msg = format(messages[messages.length - 1], args);
		$(element).find(display[display.length - 1]).html(msg);
	}
	return counts;
}

function HierarchicalHitCounter (element, hits, labels, display, searching_messages, done_messages) {
	this.element = element;
	this.hits = hits;
	this.labels = labels;
	this.display = display;
	this.searching_messages = searching_messages;
	this.done_messages = done_messages;
	this.done = false;
	this.updates = 0;

	this.update = function () {
		var ndots = 4;
		var throbber = repeat('.', this.updates % ndots) + ' ' + repeat('.', ndots - this.updates % ndots - 1);
		countHits(this.element, this.hits, this.labels, this.display, 
				(this.done ? this.done_messages : this.searching_messages),
				throbber);
		this.updates++;
	}
	
	this.auto_update = function (delay) {
		var obj = this;
		if (!delay) {
			delay = 500;
		}
		function callback () {
			obj.update();
			if (!obj.done) {
				window.setTimeout(callback, delay);
			}
		}
		callback();
		return this;
	}
	
	this.done_when_ready = function () {
		var obj = this;
		$(document).ready(function () { 
			obj.done = true; 
			obj.update(); });
		return this;
	}
	
	return this;
}