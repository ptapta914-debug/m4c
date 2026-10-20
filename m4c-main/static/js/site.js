const header = document.querySelector('#siteHeader');
const menuToggle = document.querySelector('#menuToggle');
const primaryNav = document.querySelector('#primaryNav');

function updateHeader() {
  header?.classList.toggle('is-scrolled', window.scrollY > 20);
}
window.addEventListener('scroll', updateHeader, { passive: true });
updateHeader();

menuToggle?.addEventListener('click', () => {
  const isOpen = menuToggle.getAttribute('aria-expanded') === 'true';
  menuToggle.setAttribute('aria-expanded', String(!isOpen));
  menuToggle.setAttribute('aria-label', isOpen ? 'Open menu' : 'Close menu');
  primaryNav?.classList.toggle('is-open', !isOpen);
});

primaryNav?.querySelectorAll('a').forEach((link) => {
  link.addEventListener('click', () => {
    primaryNav.classList.remove('is-open');
    menuToggle?.setAttribute('aria-expanded', 'false');
    menuToggle?.setAttribute('aria-label', 'Open menu');
  });
});

const involveTabs = document.querySelector('.involve-tabs');
involveTabs?.querySelectorAll('button[data-involve-panel]').forEach((tab) => {
  tab.addEventListener('click', () => {
    involveTabs.querySelectorAll('button[data-involve-panel]').forEach((item) => {
      const isSelected = item === tab;
      item.setAttribute('aria-pressed', String(isSelected));
      const panel = document.getElementById(item.dataset.involvePanel);
      if (panel) panel.hidden = !isSelected;
    });
  });
});

const form = document.querySelector('#volunteerForm');
const status = document.querySelector('#formStatus');
const submitButton = document.querySelector('#formSubmit');
const csrfFailureMessage = 'Your form security token expired. Reload the page and try again.';

async function submitVolunteer(payload, csrfToken) {
  return fetch(form.action, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    body: JSON.stringify(payload),
  });
}

async function refreshCsrfToken() {
  const response = await fetch(window.location.href, { cache: 'no-store' });
  if (!response.ok) return null;

  const page = new DOMParser().parseFromString(await response.text(), 'text/html');
  const token = page.querySelector('#volunteerForm input[name="csrfmiddlewaretoken"]')?.value;
  if (token) form.querySelector('input[name="csrfmiddlewaretoken"]').value = token;
  return token || null;
}

async function responseJson(response) {
  const contentType = response.headers.get('content-type') || '';
  return contentType.includes('application/json') ? response.json() : null;
}

form?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const fields = new FormData(form);
  const csrfToken = fields.get('csrfmiddlewaretoken');
  const payload = Object.fromEntries(fields.entries());
  delete payload.csrfmiddlewaretoken;

  status.hidden = false;
  status.className = 'form-status';
  status.textContent = 'Registering...';
  submitButton.disabled = true;

  try {
    let response = await submitVolunteer(payload, csrfToken);
    let result = await responseJson(response);
    if (response.status === 403 && result?.message === csrfFailureMessage) {
      const freshToken = await refreshCsrfToken();
      if (freshToken) {
        response = await submitVolunteer(payload, freshToken);
        result = await responseJson(response);
      }
    }
    if (!result && response.status === 403) {
      throw new Error(csrfFailureMessage);
    }
    if (!result) throw new Error(`Unexpected server response (HTTP ${response.status}). Please try again.`);
    if (!response.ok) throw new Error(result.message || 'Failed to register. Please try again.');

    status.classList.add('success');
    status.textContent = result.message;
    form.reset();
  } catch (error) {
    status.classList.add('error');
    status.textContent = error instanceof Error ? error.message : 'Network error. Please check your connection.';
  } finally {
    submitButton.disabled = false;
  }
});

const countyMap = document.querySelector('#countyMap');
if (countyMap) {
  const countyName = document.querySelector('#mapCountyName');
  const countySummary = document.querySelector('#mapCountySummary');
  const countyWards = document.querySelector('#mapCountyWards');
  const searchForm = document.querySelector('#countySearchForm');
  const countySearch = document.querySelector('#countySearch');
  const mapBackButton = document.querySelector('#mapBackButton');
  let countyFeatures = [];
  let wardFeatures = [];

  const polygonsFor = (geometry) => geometry.type === 'MultiPolygon' ? geometry.coordinates : [geometry.coordinates];

  function renderFeatures(features, level) {
    const coordinates = [];
    features.forEach((feature) => {
      polygonsFor(feature.geometry).forEach((polygon) => {
        polygon.forEach((ring) => ring.forEach((point) => coordinates.push(point)));
      });
    });

    if (!coordinates.length) return;
    const longitudes = coordinates.map((point) => point[0]);
    const latitudes = coordinates.map((point) => point[1]);
    const minLongitude = Math.min(...longitudes);
    const maxLongitude = Math.max(...longitudes);
    const minLatitude = Math.min(...latitudes);
    const maxLatitude = Math.max(...latitudes);
    const scale = Math.min(
      960 / (maxLongitude - minLongitude || 1),
      960 / (maxLatitude - minLatitude || 1),
    );
    const offsetX = (1000 - (maxLongitude - minLongitude) * scale) / 2;
    const offsetY = (1000 - (maxLatitude - minLatitude) * scale) / 2;

    const projectPoint = ([longitude, latitude]) => {
      const x = offsetX + (longitude - minLongitude) * scale;
      const y = 1000 - offsetY - (latitude - minLatitude) * scale;
      return `${x},${y}`;
    };

    countyMap.replaceChildren();
    countyMap.setAttribute('viewBox', '0 0 1000 1000');
    features.forEach((feature) => {
      const featureName = level === 'counties'
        ? feature.properties.name
        : feature.properties.wardName;
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      const pathData = polygonsFor(feature.geometry)
        .map((polygon) => polygon
          .filter((ring) => Array.isArray(ring) && ring.length >= 3)
          .map((ring) => `M ${ring.map(projectPoint).join(' L ')} Z`)
          .join(' '))
        .join(' ');

      path.setAttribute('d', pathData);
      path.setAttribute('class', `county-path ${level === 'wards' ? 'ward-path' : ''}`);
      path.setAttribute('title', featureName);
      path.setAttribute('fill-rule', 'evenodd');
      path.setAttribute('tabindex', '0');
      path.setAttribute('role', 'button');
      path.setAttribute('aria-label', featureName);
      if (level === 'counties') {
        path.addEventListener('click', () => showCounty(featureName));
        path.addEventListener('keydown', (event) => {
          if (event.key === 'Enter' || event.key === ' ') showCounty(featureName);
        });
      } else {
        path.addEventListener('click', () => {
          if (countyName) countyName.textContent = featureName;
          if (countySummary) countySummary.textContent = `${feature.properties.subcountyName} sub-county. Patron assignment is pending confirmation.`;
        });
      }
      countyMap.appendChild(path);
    });
  }

  function showCounty(name) {
    const selected = countyFeatures.find((feature) => feature.properties.name.toLowerCase() === name.toLowerCase());
    if (!selected) {
      if (countySummary) countySummary.textContent = 'Choose a county from the list or select one on the map.';
      return;
    }

    const selectedWards = wardFeatures.filter((feature) => feature.properties.countyName === selected.properties.name);
    const subcounties = new Map();
    selectedWards.forEach((feature) => {
      const subcountyName = feature.properties.subcountyName;
      if (!subcounties.has(subcountyName)) subcounties.set(subcountyName, []);
      subcounties.get(subcountyName).push(feature.properties.wardName);
    });

    if (countyName) countyName.textContent = selected.properties.name;
    if (countySummary) {
      countySummary.textContent = `${subcounties.size} sub-counties and ${selectedWards.length} mapped wards. Patron assignments are pending M4C confirmation.`;
    }
    if (countyWards) {
      countyWards.replaceChildren();
      [...subcounties.entries()].sort(([first], [second]) => first.localeCompare(second)).forEach(([subcountyName, wards]) => {
        const group = document.createElement('li');
        const heading = document.createElement('strong');
        const count = document.createElement('small');
        const wardList = document.createElement('ul');
        heading.textContent = subcountyName;
        count.textContent = `${wards.length} wards`;
        wardList.className = 'ward-sublist';
        wards.sort((first, second) => first.localeCompare(second)).forEach((wardName) => {
          const ward = document.createElement('li');
          ward.textContent = wardName;
          wardList.appendChild(ward);
        });
        group.append(heading, count, wardList);
        countyWards.appendChild(group);
      });
    }

    if (countySearch) countySearch.value = selected.properties.name;
    if (mapBackButton) mapBackButton.hidden = false;
    renderFeatures(selectedWards, 'wards');
  }

  function showAllCounties() {
    if (countyName) countyName.textContent = 'Select a county';
    if (countySummary) countySummary.textContent = 'Click a county on the map or search above to view its sub-counties and ward boundaries.';
    if (countyWards) countyWards.replaceChildren();
    if (countySearch) countySearch.value = '';
    if (mapBackButton) mapBackButton.hidden = true;
    renderFeatures(countyFeatures, 'counties');
  }

  searchForm?.addEventListener('submit', (event) => {
    event.preventDefault();
    if (countySearch?.value.trim()) showCounty(countySearch.value.trim());
  });
  mapBackButton?.addEventListener('click', showAllCounties);

  Promise.all([
    fetch('/static/data/kenya-counties.geojson').then((response) => {
      if (!response.ok) throw new Error('County boundary request failed');
      return response.json();
    }),
    fetch('/static/data/kenya-wards.geojson').then((response) => {
      if (!response.ok) throw new Error('Ward boundary request failed');
      return response.json();
    }),
  ])
    .then(([countyGeojson, wardGeojson]) => {
      countyFeatures = countyGeojson.features || [];
      wardFeatures = wardGeojson.features || [];
      showAllCounties();
    })
    .catch(() => {
      if (countyName) countyName.textContent = 'Map unavailable';
      if (countySummary) countySummary.textContent = 'The county and ward boundary data could not be loaded.';
    });
}
