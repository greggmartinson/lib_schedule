const PRESENTATION_ID = '12lNrWDhZ95yRpCrf2LoMvkxFhbHJz7WEUAv-asPhgdU';
const DEFAULT_SLIDE_INDEX = 2;
const SLIDE_WIDTH = 960;
const SLIDE_HEIGHT = 540;

const COLORS = {
  background: '#FFFFFF',
  title: '#E39B8A',
  headerFill: '#D18D2F',
  bodyFill: '#FFB04A',
  headerText: '#FFFFFF',
  bodyText: '#6D4613',
  divider: '#FFF4E5',
  stripeBlue: '#5C6F8A',
  stripeBeige: '#E2BA86',
  stripeSalmon: '#E49A8B',
  stripeSage: '#C9C8B2',
};

function doGet() {
  return HtmlService.createHtmlOutput(
    '<h2>Library Schedule Slide Sync</h2>' +
      '<p>This Apps Script web app is ready.</p>' +
      '<p>Run <code>python3 sync_google_slides.py</code> on your Mac to send the latest summary.</p>'
  );
}

function doPost(e) {
  try {
    const payload = parsePayload_(e);
    const result = updateScheduleSlide_(payload);
    return HtmlService.createHtmlOutput(
      '<h2>Google Slides updated</h2>' +
        '<p>Slide ' +
        result.slideIndex +
        ' was updated for ' +
        escapeHtml_(result.reportDateLabel) +
        '.</p>' +
        '<p>You can close this tab and return to Google Slides.</p>'
    );
  } catch (error) {
    return HtmlService.createHtmlOutput(
      '<h2>Update failed</h2><pre>' + escapeHtml_(String(error)) + '</pre>'
    );
  }
}

function parsePayload_(e) {
  if (e && e.parameter && e.parameter.payload) {
    return JSON.parse(e.parameter.payload);
  }

  if (e && e.postData && e.postData.contents) {
    return JSON.parse(e.postData.contents);
  }

  throw new Error('Missing schedule payload.');
}

function updateScheduleSlide_(payload) {
  const presentationId = payload.presentationId || PRESENTATION_ID;
  const slideIndex = Number(payload.slideIndex || DEFAULT_SLIDE_INDEX);
  const rooms = Array.isArray(payload.rooms) ? payload.rooms : [];
  const reportDateLabel = String(payload.reportDateLabel || '');
  const generatedAtLabel = String(payload.generatedAtLabel || '');

  const presentation = SlidesApp.openById(presentationId);
  const slides = presentation.getSlides();
  if (slideIndex < 1 || slideIndex > slides.length) {
    throw new Error(
      'Presentation has ' + slides.length + ' slides, but requested slide ' + slideIndex + '.'
    );
  }

  const slide = slides[slideIndex - 1];
  clearSlide_(slide);
  renderBackground_(slide);
  renderAccentStripes_(slide);
  renderTitle_(slide, reportDateLabel, generatedAtLabel);
  renderScheduleTable_(slide, rooms);
  presentation.saveAndClose();

  return {
    slideIndex: slideIndex,
    reportDateLabel: reportDateLabel,
  };
}

function clearSlide_(slide) {
  const elements = slide.getPageElements();
  for (let index = elements.length - 1; index >= 0; index -= 1) {
    elements[index].remove();
  }
}

function renderBackground_(slide) {
  const shape = slide.insertTextBox('', 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT);
  shape.getFill().setSolidFill(COLORS.background);
  shape.getBorder().getLineFill().setSolidFill(COLORS.background);
  shape.getBorder().setWeight(0.1);
  shape.sendToBack();
}

function renderAccentStripes_(slide) {
  const leftTop = 24;
  const stripeWidth = 24;
  const stripeGap = 18;
  const stripeHeight = 255;
  const left = 32;
  const leftColors = [COLORS.stripeBeige, COLORS.stripeSalmon, COLORS.stripeSage];

  leftColors.forEach(function (color, index) {
    renderFillBlock_(
      slide,
      left + index * (stripeWidth + stripeGap),
      leftTop,
      stripeWidth,
      stripeHeight,
      color,
      color
    );
  });

  const bottomColors = [
    COLORS.stripeBlue,
    COLORS.stripeBeige,
    COLORS.stripeSalmon,
    COLORS.stripeSage,
  ];
  const bottomLeft = 190;
  const bottomTop = 495;
  bottomColors.forEach(function (color, index) {
    renderFillBlock_(
      slide,
      bottomLeft + index * 44,
      bottomTop,
      28,
      45,
      color,
      color
    );
  });
}

function renderTitle_(slide, reportDateLabel, generatedAtLabel) {
  const titleBox = slide.insertTextBox("Today's Guests", 140, 42, 500, 56);
  styleTextBox_(titleBox, {
    fontFamily: 'Georgia',
    fontSize: 44,
    color: COLORS.title,
    boldUntil: 0,
  });
}

function renderScheduleTable_(slide, rooms) {
  const columns = 3;
  const tableLeft = 18;
  const tableTop = 120;
  const tableWidth = 900;
  const headerHeight = 62;
  const bodyHeight = 74;
  const cellWidth = tableWidth / columns;
  const rowGroups = Math.ceil(Math.max(rooms.length, 1) / columns);

  for (let row = 0; row < rowGroups; row += 1) {
    for (let column = 0; column < columns; column += 1) {
      const room = rooms[row * columns + column] || null;
      const left = tableLeft + column * cellWidth;
      const headerTop = tableTop + row * (headerHeight + bodyHeight);
      const bodyTop = headerTop + headerHeight;

      renderTableHeaderCell_(slide, left, headerTop, cellWidth, headerHeight, room);
      renderTableBodyCell_(slide, left, bodyTop, cellWidth, bodyHeight, room);
    }
  }
}

function renderTableHeaderCell_(slide, left, top, width, height, room) {
  const shape = slide.insertTextBox(room ? String(room.name || '') : '', left, top, width, height);
  shape.getFill().setSolidFill(COLORS.headerFill);
  shape.getBorder().getLineFill().setSolidFill(COLORS.divider);
  shape.getBorder().setWeight(1);

  styleTextBox_(shape, {
    fontFamily: 'Arial',
    fontSize: 16,
    color: COLORS.headerText,
    boldUntil: room ? String(room.name || '').length : 0,
    boldFontSize: 16,
  });
}

function renderTableBodyCell_(slide, left, top, width, height, room) {
  const text = room ? formatRoomBodyText_(room) : '';
  const shape = slide.insertTextBox(text, left, top, width, height);
  shape.getFill().setSolidFill(COLORS.bodyFill);
  shape.getBorder().getLineFill().setSolidFill(COLORS.divider);
  shape.getBorder().setWeight(1);

  styleTextBox_(shape, {
    fontFamily: 'Arial',
    fontSize: 15,
    color: COLORS.bodyText,
    boldUntil: 0,
  });
}

function formatRoomBodyText_(room) {
  const entries = Array.isArray(room.entries) ? room.entries : [];
  if (!entries.length) {
    return 'Free';
  }

  const parts = [];
  entries.forEach(function (entry) {
    parts.push(cleanBookingText_(String(entry.booking || '')));
    parts.push(String(entry.when || ''));
    parts.push('');
  });
  return parts.join('\n').replace(/\n$/, '');
}

function cleanBookingText_(value) {
  const cleaned = String(value || '').replace(/\s+/g, ' ').trim();
  if (!cleaned) {
    return '';
  }

  const withoutSuffix = cleaned.replace(/\s+[A-Za-z]{4,}\d{3,}$/, '').trim();
  return withoutSuffix || cleaned;
}

function styleTextBox_(shape, options) {
  const textRange = shape.getText();
  textRange
    .getTextStyle()
    .setFontFamily(options.fontFamily || 'Arial')
    .setFontSize(options.fontSize || 13);

  if (options.color) {
    textRange.getTextStyle().setForegroundColor(options.color);
  }

  shape.getText().getParagraphStyle().setLineSpacing(110);

  const boldUntil = Number(options.boldUntil || 0);
  if (boldUntil > 0) {
    textRange
      .getRange(0, boldUntil - 1)
      .getTextStyle()
      .setBold(true)
      .setFontSize(options.boldFontSize || options.fontSize || 13);
  }
}

function renderFillBlock_(slide, left, top, width, height, fillColor, borderColor) {
  const shape = slide.insertTextBox('', left, top, width, height);
  shape.getFill().setSolidFill(fillColor);
  shape.getBorder().getLineFill().setSolidFill(borderColor);
  shape.getBorder().setWeight(0.1);
}

function escapeHtml_(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
