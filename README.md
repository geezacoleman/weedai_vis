# WeedAI Dataset Visualizer

A Python tool to scrape and visualize agricultural weed datasets from WeedAI platform.

## Features

- Scrapes dataset information from [WeedAI](https://weed-ai.sydney.edu.au/datasets)
- Visualizes datasets on an interactive map
- Shows dataset composition using pie charts
- Handles overlapping datasets at the same location

## Requirements

```
pip install pandas folium matplotlib playwright beautifulsoup4 lxml
```

You'll also need to install the Playwright browsers:
```
playwright install
```

## Usage

### Scrape and visualize

```
python weedai_handler.py --scrape
```

### Visualize existing data

```
python weedai_handler.py
```

### Custom file paths

```
python weedai_handler.py --csv custom_data.csv --output custom_map.html
```

## Map Features

- Circle size indicates dataset size (number of images)
- Circle color indicates dataset type (red for weeds, green for crops)
- Pie segments show class distribution within each dataset
- Popup cards provide detailed information about each dataset
- Overlapping datasets are arranged in a circle with lines to their true location

## License

Open source - Feel free to use and modify.
