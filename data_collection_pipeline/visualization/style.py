import matplotlib.pyplot as plt
import logging

logger = logging.getLogger(__name__)

def set_publication_style():
    """Sets a clean, publication-ready style configuration for matplotlib plots."""
    try:
        if 'seaborn-v0_8-whitegrid' in plt.style.available:
            plt.style.use('seaborn-v0_8-whitegrid')
        else:
            plt.style.use('default')
            plt.rcParams['axes.grid'] = True
            plt.rcParams['grid.alpha'] = 0.5
            plt.rcParams['grid.linestyle'] = '--'
            
        plt.rcParams['font.size'] = 11
        plt.rcParams['axes.labelsize'] = 12
        plt.rcParams['axes.titlesize'] = 13
        plt.rcParams['xtick.labelsize'] = 10
        plt.rcParams['ytick.labelsize'] = 10
        plt.rcParams['figure.titlesize'] = 15
        plt.rcParams['figure.figsize'] = (8, 6)
        plt.rcParams['axes.edgecolor'] = '#333333'
        plt.rcParams['axes.linewidth'] = 0.8
    except Exception as e:
        logger.warning(f"Error configuring matplotlib styles: {e}")
