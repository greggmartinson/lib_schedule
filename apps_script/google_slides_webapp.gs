const PRESENTATION_ID = '12lNrWDhZ95yRpCrf2LoMvkxFhbHJz7WEUAv-asPhgdU';
const DEFAULT_SLIDE_INDEX = 2;
const SLIDE_WIDTH = 960;
const SLIDE_HEIGHT = 540;
const MAX_CALENDAR_EVENTS = 3;
const RENDERER_VERSION = '2026-05-15-a';

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
      '<p>Run <code>python3 sync_google_slides.py</code> on your Mac to send the latest summary.</p>' +
      '<p>Renderer version: <code>' + escapeHtml_(RENDERER_VERSION) + '</code></p>'
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
        '<p>Renderer version: <code>' +
        escapeHtml_(RENDERER_VERSION) +
        '</code></p>' +
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
  const calendar = payload.calendar || null;
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
  try {
    renderBackground_(slide);
    renderAccentStripes_(slide);
    renderTitle_(slide, reportDateLabel, generatedAtLabel);
    renderScheduleTable_(slide, rooms, calendar);
    renderRendererStamp_(slide);
  } catch (error) {
    clearSlide_(slide);
    renderFailureSlide_(slide, error, reportDateLabel);
    presentation.saveAndClose();
    throw new Error('Renderer ' + RENDERER_VERSION + ' failed: ' + String(error));
  }
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
  const titleText = reportDateLabel || "Today's Guests";
  const titleBox = slide.insertTextBox(titleText, 140, 38, 520, 30);
  styleTextBox_(titleBox, {
    fontFamily: 'Arial',
    fontSize: 24,
    color: COLORS.title,
    boldUntil: titleText.length,
    boldFontSize: 24,
    lineSpacing: 100,
  });
}

function renderRendererStamp_(slide) {
  const shape = slide.insertTextBox(
    'Renderer ' + RENDERER_VERSION,
    748,
    500,
    180,
    18
  );
  styleTextBox_(shape, {
    fontFamily: 'Arial',
    fontSize: 8,
    color: '#B07F4B',
    boldUntil: 0,
    lineSpacing: 100,
  });
}

function renderFailureSlide_(slide, error, reportDateLabel) {
  renderBackground_(slide);
  const heading = slide.insertTextBox('Slide sync failed', 60, 70, 360, 36);
  heading.getText().getTextStyle().setBold(true).setFontSize(22).setForegroundColor('#8B2E2E');

  const details = slide.insertTextBox(
    'Date: ' +
      String(reportDateLabel || '') +
      '\nRenderer: ' +
      RENDERER_VERSION +
      '\nError: ' +
      String(error),
    60,
    120,
    840,
    220
  );
  details.getText().getTextStyle().setFontFamily('Arial').setFontSize(14).setForegroundColor('#333333');
}

function renderScheduleTable_(slide, rooms, calendar) {
  const tableLeft = 42;
  const tableTop = 86;
  const tableWidth = 800;
  const tableHeight = 392;
  const gap = 10;

  if (!calendar) {
    renderRoomGrid_(slide, rooms, tableLeft, tableTop, tableWidth, tableHeight, 4, gap);
    return;
  }

  const calendarHeight = 132;
  const roomGridHeight = tableHeight - calendarHeight - gap;
  renderRoomGrid_(slide, rooms, tableLeft, tableTop, tableWidth, roomGridHeight, 4, gap);
  renderCalendarPanel_(
    slide,
    calendar,
    tableLeft,
    tableTop + roomGridHeight + gap,
    tableWidth,
    calendarHeight
  );
}

function renderRoomGrid_(slide, rooms, left, top, width, height, columns, gap) {
  const cards = rooms.slice();
  const rows = Math.ceil(Math.max(cards.length, 1) / columns);
  const cellWidth = (width - gap * (columns - 1)) / columns;
  const cellHeight = (height - gap * Math.max(rows - 1, 0)) / rows;
  const headerHeight = 42;
  const bodyHeight = cellHeight - headerHeight;

  for (let row = 0; row < rows; row += 1) {
    for (let column = 0; column < columns; column += 1) {
      const card = cards[row * columns + column] || null;
      const cellLeft = left + column * (cellWidth + gap);
      const headerTop = top + row * (cellHeight + gap);
      const bodyTop = headerTop + headerHeight;

      renderTableHeaderCell_(
        slide,
        cellLeft,
        headerTop,
        cellWidth,
        headerHeight,
        card ? String(card.name || '') : ''
      );
      renderTableBodyCell_(
        slide,
        cellLeft,
        bodyTop,
        cellWidth,
        bodyHeight,
        card ? formatRoomBodyText_(card) : '',
        {
          fontSize: 13,
          lineSpacing: 105,
        }
      );
    }
  }
}

function renderCalendarPanel_(slide, calendar, left, top, width, height) {
  const headerHeight = 48;
  renderTableHeaderCell_(
    slide,
    left,
    top,
    width,
    headerHeight,
    formatCalendarHeading_(calendar)
  );
  renderTableBodyCell_(
    slide,
    left,
    top + headerHeight,
    width,
    height - headerHeight,
    formatCalendarBodyText_(calendar),
    {
      fontSize: 12,
      lineSpacing: 102,
    }
  );
}

function renderTableHeaderCell_(slide, left, top, width, height, headerText) {
  const shape = slide.insertTextBox(headerText, left, top, width, height);
  shape.getFill().setSolidFill(COLORS.headerFill);
  shape.getBorder().getLineFill().setSolidFill(COLORS.divider);
  shape.getBorder().setWeight(1);

  styleTextBox_(shape, {
    fontFamily: 'Arial',
    fontSize: 15,
    color: COLORS.headerText,
    boldUntil: headerText.length,
    boldFontSize: 15,
  });
}

function renderTableBodyCell_(slide, left, top, width, height, text, options) {
  const shape = slide.insertTextBox(text, left, top, width, height);
  shape.getFill().setSolidFill(COLORS.bodyFill);
  shape.getBorder().getLineFill().setSolidFill(COLORS.divider);
  shape.getBorder().setWeight(1);

  styleTextBox_(shape, {
    fontFamily: 'Arial',
    fontSize: (options && options.fontSize) || 15,
    color: COLORS.bodyText,
    boldUntil: 0,
    lineSpacing: (options && options.lineSpacing) || 110,
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

function formatCalendarHeading_(calendar) {
  const sourceName = String((calendar && calendar.sourceName) || '').trim();
  return sourceName ? sourceName + ' Events' : 'Calendar Events';
}

function formatCalendarBodyText_(calendar) {
  const statusNote = String((calendar && calendar.statusNote) || '').trim();
  if (statusNote) {
    return statusNote;
  }

  const events = Array.isArray(calendar && calendar.events) ? calendar.events : [];
  if (!events.length) {
    return 'No calendar events today.';
  }

  const parts = [];
  events.slice(0, MAX_CALENDAR_EVENTS).forEach(function (event) {
    const title = String((event && event.title) || '').trim();
    if (!title) {
      return;
    }
    parts.push(title);

    const when = String((event && event.when) || '').trim();
    const details = String((event && event.details) || '').trim();
    if (when) {
      parts.push(when);
    }
    if (details) {
      parts.push(details);
    }
    parts.push('');
  });

  const remaining = events.length - MAX_CALENDAR_EVENTS;
  if (remaining > 0) {
    parts.push('+' + remaining + ' more');
  }
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

  shape.getText().getParagraphStyle().setLineSpacing(options.lineSpacing || 110);

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
