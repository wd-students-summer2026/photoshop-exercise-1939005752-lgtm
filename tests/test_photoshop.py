"""
Tests for the Raster Image (Photoshop / GIMP) assignment.

The student must:
  - publish a `photoshop.html` page that displays their raster image
  - link to that page from their personal site's home page
  - serve a real JPEG or PNG image on the page (not a vector or GIF)

Subjective requirements (six layers, layer masks, "realism", filters,
etc.) cannot be verified automatically and are intentionally not tested.

Requires Selenium 4.6+ and Google Chrome.
"""

import json
import pytest
from urllib.parse import urljoin
from urllib.request import urlopen, Request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException


PAGE = "photoshop.html"
MIN_IMAGE_DIMENSION_PX = 400  # a postage-stamp wouldn't satisfy the assignment


def _build_url(site_url, page=""):
  base = site_url.rstrip("/")
  if not page:
    return base + "/"
  return base + "/" + page.lstrip("/")


def _content_type(url):
  try:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=10) as resp:
      return resp.headers.get("Content-Type", "").lower(), resp.read(8)
  except Exception:
    return "", b""


class Tests:

  @pytest.fixture(scope="class")
  def settings(self):
    with open('./settings.json', 'r') as f:
      yield json.load(f)

  @pytest.fixture(scope="class")
  def page_url(self, settings):
    return _build_url(settings["site_url"], PAGE)

  @pytest.fixture(scope="class")
  def driver(self, page_url):
    options = Options()
    options.add_argument("--window-size=1400,1000")
    driver = webdriver.Chrome(options=options)
    driver.get(page_url)
    yield driver
    driver.quit()

  def test_page_loads(self, driver):
    """photoshop.html must load successfully."""
    assert driver.find_element(By.TAG_NAME, "body")

  def test_has_image(self, driver):
    """An <img> element must be present on photoshop.html."""
    imgs = driver.find_elements(By.TAG_NAME, "img")
    assert imgs, "No <img> elements on photoshop.html."

  def test_image_is_raster(self, driver, page_url):
    """
    The page must display at least one real JPEG or PNG image. We check
    both the file extension and the response Content-Type / magic bytes.
    """
    imgs = driver.find_elements(By.TAG_NAME, "img")
    raster_url = None
    for img in imgs:
      src = img.get_attribute("src") or ""
      if not src:
        continue
      abs_src = urljoin(page_url, src)
      ct, head = _content_type(abs_src)
      is_jpeg = (
        abs_src.lower().endswith((".jpg", ".jpeg"))
        or "jpeg" in ct
        or head[:3] == b"\xff\xd8\xff"
      )
      is_png = (
        abs_src.lower().endswith(".png")
        or "png" in ct
        or head[:8] == b"\x89PNG\r\n\x1a\n"
      )
      if is_jpeg or is_png:
        raster_url = abs_src
        break
    assert raster_url, (
      "No <img> on photoshop.html points to a JPEG or PNG file. The "
      "README requires a flat raster image (not a vector or GIF)."
    )

  def test_image_dimensions_reasonable(self, driver):
    """
    The displayed raster image must be at least {min}x{min} pixels in
    its natural size.
    """.format(min=MIN_IMAGE_DIMENSION_PX)
    dims = driver.execute_async_script(
      """
      var min = arguments[0];
      var done = arguments[1];
      var imgs = document.querySelectorAll('img');
      function check(i) {
        if (i >= imgs.length) return done([0, 0]);
        var img = imgs[i];
        var src = img.src || '';
        if (!/\\.(png|jpe?g)(\\?|#|$)/i.test(src)) return check(i + 1);
        var probe = new Image();
        probe.onload = function () {
          if (probe.naturalWidth >= min && probe.naturalHeight >= min) {
            done([probe.naturalWidth, probe.naturalHeight]);
          } else {
            check(i + 1);
          }
        };
        probe.onerror = function () { check(i + 1); };
        probe.src = src;
      }
      check(0);
      """,
      MIN_IMAGE_DIMENSION_PX,
    )
    assert (
      dims and dims[0] >= MIN_IMAGE_DIMENSION_PX
      and dims[1] >= MIN_IMAGE_DIMENSION_PX
    ), (
      "No raster <img> on photoshop.html is at least {min}x{min}px. "
      "Got {got}.".format(min=MIN_IMAGE_DIMENSION_PX, got=dims)
    )

  def test_images_have_alt(self, driver):
    """Every <img> must have a non-empty alt attribute."""
    for img in driver.find_elements(By.TAG_NAME, "img"):
      alt = img.get_attribute("alt")
      assert alt is not None and alt.strip() != "", (
        "An <img> on photoshop.html is missing an alt attribute: {}"
        .format(img.get_attribute("src"))
      )

  def test_linked_from_home(self, settings):
    """The home page (index.html) must link to photoshop.html."""
    home = _build_url(settings["site_url"])
    options = Options()
    options.add_argument("--window-size=1400,1000")
    driver = webdriver.Chrome(options=options)
    try:
      driver.get(home)
      try:
        elem = driver.find_element(
          By.CSS_SELECTOR,
          "a[href='{0}'], a[href$='/{0}']".format(PAGE),
        )
      except NoSuchElementException:
        elem = None
      assert elem, "The home page has no link to photoshop.html."
    finally:
      driver.quit()
