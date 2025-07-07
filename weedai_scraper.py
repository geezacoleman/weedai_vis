import pandas as pd
import folium
import math
import matplotlib.pyplot as plt
import io
import base64
import csv
import re
import html
from collections import Counter
from typing import Dict, List, Optional, Any
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup


class WeedAIHandler:
    """
    A class to handle scraping and visualization of WeedAI datasets
    """

    def __init__(self, csv_path: str = 'weedai_full.csv', output_html: str = 'index.html'):
        """
        Initialize the WeedAI handler

        Args:
            csv_path: Path to save or load the CSV file
            output_html: Path to save the HTML visualization
        """
        self.csv_path = csv_path
        self.output_html = output_html
        self.dataset_info = {}
        self.type_colors = {
            'weed': '#003f5c',
            'crop': '#bc5090',
            'unknown': '#ffa600'
        }
        self.df = None

    def scrape_datasets(self) -> None:
        """
        Scrape dataset information from WeedAI website
        """
        results = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto("https://weed-ai.sydney.edu.au/datasets", wait_until="networkidle")
            listing_html = page.content()
            listing_soup = BeautifulSoup(listing_html, "lxml")

            for tr in listing_soup.select("tbody.MuiTableBody-root tr"):
                a = tr.select_one("th.MuiTableCell-body a.MuiLink-root")
                name = a.get_text(strip=True)
                print(f'[INFO] Collecting data from {name} dataset')
                href = a["href"]
                if href.startswith("/"):
                    href = "https://weed-ai.sydney.edu.au" + href
                    print(f'VISITING: {href}')

                page.goto(href, wait_until="networkidle")
                detail_html = page.content()
                dsoup = BeautifulSoup(detail_html, "lxml")

                sample_p = dsoup.find("p", string=re.compile(r"Sample of\s+\d+\s+Images"))
                total_images = int(re.search(r"\d+", sample_p.get_text()).group())

                h4_loc = dsoup.find("h4", string="Location")
                loc_card = h4_loc.find_parent("div", class_="MuiCardContent-root")
                lat, lon = [c.strip() for c in loc_card.find("p").get_text().split(",", 1)]

                summary_p = dsoup.find("p", string="Annotation Statistics")
                accordion = summary_p.find_parent("div", class_="MuiAccordion-root")
                details = accordion.find("div", class_="MuiAccordionDetails-root")

                for stat_tr in details.select("tbody.MuiTableBody-root tr"):
                    cells = stat_tr.find_all("td")
                    raw_category = cells[0].get_text(strip=True)
                    n_class_images = int(cells[1].get_text(strip=True))
                    n_boxes = int(cells[3].get_text(strip=True))

                    if ":" in raw_category:
                        type_, rest = raw_category.split(":", 1)
                        type_ = type_.strip()
                        rest = rest.strip()
                    else:
                        type_ = None
                        rest = raw_category

                    m = re.match(r"(.+?)\s*\((.+)\)", rest)
                    if m:
                        cls_name = m.group(1).strip()
                        sub_cat = m.group(2).strip()
                    else:
                        cls_name = rest
                        sub_cat = None

                    results.append([
                        name,
                        href,
                        total_images,
                        lat,
                        lon,
                        type_,
                        cls_name,
                        sub_cat,
                        n_boxes,
                        n_class_images,
                    ])

            browser.close()

        # Write results to CSV
        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "dataset_name",
                "url",
                "total_images",
                "latitude",
                "longitude",
                "type",
                "class",
                "class_sub_cat",
                "n_boxes",
                "n_class_images",
            ])
            writer.writerows(results)

        print(f"✅ Wrote {len(results)} rows to {self.csv_path}")

    def load_data(self) -> None:
        """
        Load dataset information from CSV file
        """
        try:
            self.df = pd.read_csv(self.csv_path)
            self.df['longitude'] = pd.to_numeric(self.df['longitude'], errors='coerce')
        except KeyError:
            self.df = pd.read_csv(self.csv_path, sep=';')
            self.df['longitude'] = pd.to_numeric(self.df['longitude'], errors='coerce')

        self.df = self.df.dropna(subset=['latitude', 'longitude'])

        # Process data and build dataset_info dictionary
        for _, row in self.df.iterrows():
            dataset_name = row['dataset_name']

            if dataset_name not in self.dataset_info:
                self.dataset_info[dataset_name] = {
                    'total_images': row['total_images'],
                    'latitude': row['latitude'],
                    'longitude': row['longitude'],
                    'classes': [],
                    'n_boxes': row['n_boxes'] if pd.notna(row['n_boxes']) else 0,
                    'url': row['url']
                }

            if pd.notna(row['class']) and row['class'] != 'none':
                self.dataset_info[dataset_name]['classes'].append({
                    'class_name': row['class'],
                    'type': row['type'] if pd.notna(row['type']) else 'unknown',
                    'n_class_images': row['n_class_images'] if pd.notna(row['n_class_images']) else 0,
                    'class_sub_cat': row['class_sub_cat'] if pd.notna(row['class_sub_cat']) else None
                })

        print(f"Loaded {len(self.dataset_info)} datasets from {self.csv_path}")

    def apply_jittering(self) -> None:
        """
        Apply organized jittering to datasets at the same location
        """
        location_counter = Counter()
        for info in self.dataset_info.values():
            location_tuple = (info['latitude'], info['longitude'])
            location_counter[location_tuple] += 1

        for location, count in location_counter.items():
            if count > 1:
                datasets_at_location = [
                    (name, info) for name, info in self.dataset_info.items()
                    if (info['latitude'], info['longitude']) == location
                ]

                for name, info in datasets_at_location:
                    info['original_latitude'] = info['latitude']
                    info['original_longitude'] = info['longitude']

                jitter_radius = min(0.1, 0.05 * math.log(count + 1))  # Radius of the circle of jittered points

                for i, (name, info) in enumerate(datasets_at_location):
                    angle = (2 * math.pi * i) / count

                    info['latitude'] = location[0] + jitter_radius * math.sin(angle)
                    info['longitude'] = location[1] + jitter_radius * math.cos(angle)

    def create_pie_chart(self, classes: List[Dict], radius: int = 50) -> Optional[str]:
        """
        Create a pie chart visualization of classes

        Args:
            classes: List of class information dictionaries
            radius: Radius of the pie chart in pixels

        Returns:
            Base64 encoded PNG image or None if no classes
        """
        if not classes:
            return None

        classes = sorted(classes, key=lambda x: x['n_class_images'], reverse=True)
        class_values = [c['n_class_images'] for c in classes]
        colors = []
        for i, c in enumerate(classes):
            type_value = c['type'] if c['type'] is not None else 'unknown'
            base_color = self.type_colors.get(type_value, self.type_colors['unknown'])

            r = int(base_color[1:3], 16)
            g = int(base_color[3:5], 16)
            b = int(base_color[5:7], 16)

            factor = 0.7 + 0.3 * (i / max(1, len(classes) - 1)) * 2

            new_r = min(255, int(r * factor))
            new_g = min(255, int(g * factor))
            new_b = min(255, int(b * factor))

            colors.append(f'#{new_r:02x}{new_g:02x}{new_b:02x}')

        fig, ax = plt.subplots(figsize=(radius / 25, radius / 25), dpi=100)
        if len(class_values) == 1:
            type_value = classes[0]['type'] if classes[0]['type'] is not None else 'unknown'
            base_color = self.type_colors.get(type_value, self.type_colors['unknown'])

            circle = plt.Circle((0.5, 0.5), 0.5, color=base_color)
            ax.add_patch(circle)
        else:
            wedges, _ = ax.pie(class_values, colors=colors,
                               wedgeprops=dict(edgecolor='w', linewidth=1.0))

        ax.set_aspect('equal')
        ax.axis('off')

        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', transparent=True)
        plt.close(fig)
        buf.seek(0)

        img_str = base64.b64encode(buf.read()).decode()
        return img_str

    def scale_radius(self, total_images: int) -> float:
        """
        Scale the radius of markers based on total images

        Args:
            total_images: Number of images in the dataset

        Returns:
            Scaled radius value
        """
        min_size = 20
        max_size = 100
        min_images = min(info['total_images'] for info in self.dataset_info.values())
        max_images = max(info['total_images'] for info in self.dataset_info.values())

        if total_images <= 0:
            return min_size

        scaled = min_size + (max_size - min_size) * (math.log(total_images) - math.log(min_images)) / (
                math.log(max_images) - math.log(min_images))
        return scaled

    def create_map(self) -> None:
        """
        Create and save an interactive map visualization with clustering
        """
        lats = [info['latitude'] for info in self.dataset_info.values()]
        lons = [info['longitude'] for info in self.dataset_info.values()]
        avg_lat = sum(lats) / len(lats)
        avg_lon = sum(lons) / len(lons)
        map_center = [avg_lat, avg_lon]

        m = folium.Map(location=map_center, zoom_start=3, tiles='OpenStreetMap')

        from folium import plugins
        marker_cluster = plugins.MarkerCluster(
            name='Dataset Clusters',
            overlay=True,
            control=True,
            icon_create_function=None  # Use default cluster icons
        )

        for dataset_name, info in self.dataset_info.items():
            if 'original_latitude' in info:
                folium.PolyLine(
                    locations=[
                        [info['latitude'], info['longitude']],
                        [info['original_latitude'], info['original_longitude']]
                    ],
                    color='#888888',  # Light gray
                    weight=1.5,  # Thin line
                    opacity=0.5,  # Semi-transparent
                    dash_array='5, 5'  # Dashed line
                ).add_to(m)

        for dataset_name, info in self.dataset_info.items():
            radius = self.scale_radius(info['total_images'])
            popup_content = self._create_popup_content(dataset_name, info)

            pie_img = self.create_pie_chart(info['classes'], radius=radius * 2)

            if pie_img:
                icon_html = f'''
                <div style="
                    background-color: transparent;
                    width: {radius * 2}px;
                    height: {radius * 2}px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    border-radius: 50%;
                    overflow: hidden;
                ">
                    <img src="data:image/png;base64,{pie_img}" style="width: 100%; height: 100%;">
                </div>
                '''

                icon = folium.DivIcon(
                    icon_size=(radius * 2, radius * 2),
                    icon_anchor=(radius, radius),
                    html=icon_html
                )

                marker = folium.Marker(
                    location=[info['latitude'], info['longitude']],
                    icon=icon,
                    popup=folium.Popup(popup_content, max_width=500)
                )
                marker_cluster.add_child(marker)
            else:
                default_color = self._get_default_color(info)

                folium.CircleMarker(
                    location=[info['latitude'], info['longitude']],
                    radius=radius / 2,
                    color=default_color,
                    weight=0,
                    fill=True,
                    fill_color=default_color,
                    fill_opacity=0.75,
                    popup=folium.Popup(popup_content, max_width=500)
                ).add_to(marker_cluster)

        marker_cluster.add_to(m)

        self._add_title_and_legend(m)
        m.save(self.output_html)
        print(f"Map saved as '{self.output_html}'")

    def _create_popup_content(self, dataset_name: str, info: Dict[str, Any]) -> str:
        """
        Build the HTML for each marker popup,
        injecting a star button and count span that rely on LocalStorage.
        """
        url = info['url']
        classes = info.get('classes', [])
        class_list = "".join(f"<li>{c['class_name']} ({c['type']})</li>" for c in classes)

        return f"""
        <div class="dataset-popup" data-name="{dataset_name}">
          <strong>{dataset_name}</strong><br>
          <strong>URL:</strong>
            <a href="{url}" target="_blank">Dataset Link</a><br>

          <!-- star button & client-side counter -->
          <button
            class="star-btn"
            onclick="recordStar(this); return false;"
            style="border:none; background:transparent; cursor:pointer; font-size:1.2rem;"
            aria-label="Star this dataset"
          >⭐</button>
          <span class="star-count">0</span><br>

          <strong>Classes:</strong>
          <ul>{class_list}</ul>
        </div>
        """

    def _get_default_color(self, info: Dict) -> str:
        """
        Get default color for a dataset when pie chart fails

        Args:
            info: Dataset information dictionary

        Returns:
            Hex color code
        """
        if len(info['classes']) == 0:
            return '#888888'
        elif len(info['classes']) == 1:
            class_type = info['classes'][0]['type']
            if class_type is None or class_type == '':
                return self.type_colors['unknown']
            else:
                return self.type_colors.get(class_type, self.type_colors['unknown'])
        else:
            class_type = info['classes'][0]['type']
            return self.type_colors.get(class_type, self.type_colors['unknown']) if class_type else self.type_colors[
                'unknown']

    def _add_title_and_legend(self, m: folium.Map) -> None:
        num_crops = self.df.loc[self.df['type'] == 'crop', 'class'].nunique()
        num_weeds = self.df.loc[self.df['type'] == 'weed', 'class'].nunique()
        num_objects = self.df['n_boxes'].fillna(0).sum()
        total_images = (self.df.drop_duplicates(subset='dataset_name')['total_images'].fillna(0).sum())

        stats_html = f"""
        <div class="page-stats" id="page-stats">
          <span><strong>Annotated Crop Species:</strong> {num_crops}</span>
          <span><strong>Annotated Weed Species:</strong> {num_weeds}</span>
          <span><strong>Total Objects:</strong> {num_objects}</span>
          <span><strong>Total Images:</strong> {total_images}</span>

          <!-- leaderboard toggle -->
          <button id="toggle-leaderboard" type="button">
            Show Leaderboard
          </button>
        </div>
        """

        # Link to external CSS files
        css_links = """
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
              integrity="sha512-iecdLmaskl7CVkqkXNQ/ZH/XLlvWZOJyj7Yy7tcenmpD1ypASozpmT/E0iPtmFIB46ZmdtAc9eNBvH0H/ZpiBw=="
              crossorigin="anonymous" referrerpolicy="no-referrer" />
        <link rel="stylesheet" href="/static/css/main.css">
        <link rel="stylesheet" href="/static/css/clusters.css">
        <link rel="stylesheet" href="/static/css/mobile.css">
        """
        m.get_root().html.add_child(folium.Element(css_links))

        header = """
        <!-- Page header -->
        <header class="page-header">
          <div class="header-left">
            <div class="logo-section">
              <h1 onclick="window.location.href='/'">WeedAI Dataset Map</h1>
              <p>Explore agricultural weed datasets worldwide</p>
            </div>
          </div>
          <nav class="nav-links">
            <a href="/" class="active">Map</a>
            <a href="/datasets.html">Datasets</a>
            <a href="/about.html">About</a>
            <a href="/how-to-upload.html">How to Upload</a>
            <a href="https://weed-ai.sydney.edu.au/upload" target="_blank" class="btn-upload">Upload</a>
          </nav>
        </header>
        """
        m.get_root().html.add_child(folium.Element(header))
        m.get_root().html.add_child(folium.Element(stats_html))

        legend = """
        <div class="legend">
          <h5>Dataset Class Types</h5>
          <ul>
            <li><span class="dot" style="background:#003f5c;"></span>Weed</li>
            <li><span class="dot" style="background:#bc5090;"></span>Crop</li>
          </ul>
          <h5>Size &amp; Segments</h5>
          <ul>
            <li>
              <span style="display:flex; align-items:center; margin-right:0.5rem;">
                <span style="width:4px; height:4px; background:#888;
                             border-radius:50%; margin-right:4px;"></span>
                <span style="width:8px; height:8px; background:#888;
                             border-radius:50%; margin-right:4px;"></span>
                <span style="width:12px; height:12px; background:#888;
                             border-radius:50%;"></span>
              </span>
              Image number
            </li>
            <li><span class="pie-icon"></span>Class proportions</li>
          </ul>
          <small style="color:#888;">Dataset locations are approximated</small>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend))

        # Collapsible sidebar leaderboard
        leaderboard_html = """
        <!-- Sidebar leaderboard -->
        <div id="leaderboard">
          <h5 style="margin-top:0;">Most-Starred Datasets</h5>
          <ol id="leaderboard-list"></ol>
        </div>
        """
        m.get_root().html.add_child(folium.Element(leaderboard_html))

        # Link to external JavaScript
        js_link = '<script src="/static/js/weedai.js"></script>'
        m.get_root().html.add_child(folium.Element(js_link))

        # Persistent footer
        footer_html = """
        <footer>
          <div class="author">Built by Guy Coleman</div>
          <div class="social-links">
            <div class="social-icons">
              <a href="https://github.com/geezacoleman/weedai_vis" target="_blank" aria-label="GitHub">
                <i class="fab fa-github"></i>
              </a>
              <a href="https://www.youtube.com/channel/UCQxrZOfuLxlNM1i-gAueoLw" target="_blank" aria-label="YouTube">
                <i class="fab fa-youtube"></i>
              </a>
              <a href="https://www.linkedin.com/in/guy-coleman/" target="_blank" aria-label="LinkedIn">
                <i class="fab fa-linkedin"></i>
              </a>
            </div>
            <div class="version">V0.1.0</div>
          </div>
        </footer>
        """
        m.get_root().html.add_child(folium.Element(footer_html))

    def run_scrape_and_visualize(self) -> None:
        """
        Run the complete process: scrape data and create visualization
        """
        self.scrape_datasets()
        self.load_data()
        self.apply_jittering()
        self.create_map()

    def run_visualize_only(self) -> None:
        """
        Run visualization only using existing CSV file
        """
        self.load_data()
        self.apply_jittering()
        self.create_map()


def main():
    """Main function to run the script"""
    import argparse

    parser = argparse.ArgumentParser(description="WeedAI Dataset Scraper and Visualizer")
    parser.add_argument("--scrape", action="store_true", help="Scrape data from WeedAI website")
    parser.add_argument("--csv", default="weedai_data.csv", help="CSV file path")
    parser.add_argument("--output", default="index.html", help="Output HTML file path")

    args = parser.parse_args()

    weedai = WeedAIHandler(csv_path=args.csv, output_html=args.output)

    if args.scrape:
        weedai.run_scrape_and_visualize()
    else:
        weedai.run_visualize_only()


if __name__ == "__main__":
    main()
