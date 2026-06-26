#!/usr/bin/env python3
"""Download Open Access papers using Unpaywall API and direct publisher URLs."""

import os
import json
import time
import urllib.request
import urllib.error
import ssl

OUTPUT_DIR = "/Users/macbookpro/Documents/jurnal_penelitian/pdf_references"
EMAIL = "researcher@university.edu"  # For Unpaywall API

# All 38 papers with metadata
PAPERS = [
    {"id": 1, "access": "PW", "doi": "10.1117/12.3100406", "title": "Transformer-Based Energy Consumption Prediction and Optimization Framework for BIM-Enabled Green Buildings"},
    {"id": 2, "access": "PW", "doi": "10.1109/INCSST64791.2025.11210356", "title": "Research on the Application Intelligent Analysis in Industrial Energy Dissipation"},
    {"id": 3, "access": "OA", "doi": "10.1109/OJPEL.2024.3422021", "title": "Digital Twin Integration With Data Fusion for Enhanced Photovoltaic System Management"},
    {"id": 4, "access": "OA", "doi": "10.1016/j.apenergy.2025.126670", "title": "A systematic review of transformers and large language models in the energy sector"},
    {"id": 5, "access": "PW", "doi": "10.1109/ICAIS50930.2021.9395938", "title": "Impact of Federated Learning on Smart Buildings"},
    {"id": 6, "access": "PW", "doi": "10.1109/PEEIC59336.2023.10451199", "title": "Edge Computing and 5G Integration for Real-time Analytics in Interoperable Smart Grids"},
    {"id": 7, "access": "PW", "doi": "10.1016/j.jobe.2026.115416", "title": "A data-driven predictive maintenance framework for smart buildings"},
    {"id": 8, "access": "OA", "doi": "10.1007/s13369-025-10671-3", "title": "Adversarial Error Mitigation Technique for Sensor Fusion Framework"},
    {"id": 9, "access": "OA", "doi": "10.1109/ACCESS.2026.3686217", "title": "Enabling Predictive Maintenance in Smart Buildings"},
    {"id": 10, "access": "PW", "doi": "10.1016/B978-0-443-44084-7.00016-0", "title": "Digital twin based on edge computing fog computing cloud computing toward smart home"},
    {"id": 11, "access": "PW", "doi": "10.1109/CoDIT66093.2025.11321508", "title": "Enhancing Digital Continuity and Interoperability in Building Energy Management"},
    {"id": 12, "access": "PW", "doi": "10.1109/MPEL.2025.3624984", "title": "Enhanced Edge Computing for Digital Twin Applications in Energy-Intensive Industrial Systems"},
    {"id": 13, "access": "PW", "doi": "10.1109/PDP66500.2025.00078", "title": "Analysis of Time Synchronization Challenges in Digital Twins"},
    {"id": 14, "access": "OA", "doi": "10.1145/3756423.3756551", "title": "Real-Time Safety Monitoring System for Smart Construction Sites"},
    {"id": 15, "access": "OA", "doi": "10.1007/978-3-031-62273-1_33", "title": "CRISP-DM User Mobility Determined IoT Placement Within a Real-World Smart Building"},
    {"id": 16, "access": "OA", "doi": "10.3390/app11125374", "title": "Iot open-source architecture for the maintenance of building facilities"},
    {"id": 17, "access": "PW", "doi": "10.1109/ICPS49255.2021.9468219", "title": "Knowledge graphs as enhancers of intelligent digital twins"},
    {"id": 18, "access": "OA", "doi": "10.3390/su162410937", "title": "Exploring the Synergy of Advanced Lighting Controls BIM and IoT"},
    {"id": 19, "access": "OA", "doi": "10.1016/j.buildenv.2024.111355", "title": "DMFF Deep multimodel feature fusion for building occupancy detection"},
    {"id": 20, "access": "OA", "doi": "10.32604/cmc.2023.031834", "title": "Intelligent Energy Consumption For Smart Homes Using Fused Machine-Learning"},
    {"id": 21, "access": "OA", "doi": "10.1016/j.enbuild.2024.115254", "title": "A scalable approach for real-world implementation of deep reinforcement learning controllers"},
    {"id": 22, "access": "PW", "doi": "10.1061/9780784483893.061", "title": "Developing a Web-Based BIM Asset and Facility Management System"},
    {"id": 23, "access": "OA", "doi": "10.1109/ACCESS.2025.3602914", "title": "Multimodal Learning Techniques for Time Series Forecasting in Renewable Energy"},
    {"id": 24, "access": "PW", "doi": "10.1007/978-3-030-82196-8_6", "title": "The Emergence of Hybrid Edge-Cloud Computing for Energy Efficiency in Buildings"},
    {"id": 25, "access": "PW", "doi": "10.1109/NAECON58068.2023.10365788", "title": "Fusion Orchestration Guidelines for Collaborative Computing"},
    {"id": 26, "access": "OA", "doi": "10.1016/j.enbuild.2025.115723", "title": "Learning from other cities Transfer learning based multimodal residential energy prediction"},
    {"id": 27, "access": "PW", "doi": "10.1109/EEBDA53927.2022.9744878", "title": "Research on Comprehensive Energy Efficiency Control and Optimization Technology"},
    {"id": 28, "access": "OA", "doi": "10.1016/j.egyr.2026.109082", "title": "Sustainable buildings energy management with AI and machine learning"},
    {"id": 29, "access": "OA", "doi": "10.1002/itl2.70040", "title": "Design of Intelligent Building Environment Control System Based on IoT and 6G"},
    {"id": 30, "access": "PW", "doi": "10.1007/978-981-97-8313-7_83", "title": "Leveraging Multimodal Large Language Models for Building Energy Modeling"},
    {"id": 31, "access": "PW", "doi": "10.3785/j.issn.1008-973X.2026.04.005", "title": "Survey on edge deployment and inference acceleration of multimodal LLMs"},
    {"id": 32, "access": "PW", "doi": "10.1016/j.suscom.2026.101350", "title": "Integration of intelligent building operation data based on multi feature fusion"},
    {"id": 33, "access": "PW", "doi": "10.1109/AECSPE66597.2025.00108", "title": "Research on Real-Time Fusion and Intelligent Analysis Algorithm"},
    {"id": 34, "access": "PW", "doi": "10.1016/j.jobe.2025.114535", "title": "PV-GPT query the PV data using natural language"},
    {"id": 35, "access": "PW", "doi": "10.1109/ICCMC65190.2025.11140649", "title": "A Secure and Scalable IoT Architecture for Smart Energy Monitoring"},
    {"id": 36, "access": "PW", "doi": "10.1049/icp.2025.3149", "title": "Research on Prediction and Optimization Method of Building Energy Efficiency"},
    {"id": 37, "access": "OA", "doi": "10.1051/e3sconf/202568000144", "title": "Smart Digital Twin for Energy Efficiency in Buildings Using BIM IoT and AI"},
    {"id": 38, "access": "PW", "doi": "10.1109/ICACRS67045.2025.11324399", "title": "Hybrid Edge-Cloud AI and Blockchain System Architecture"},
]

def sanitize_filename(title, paper_id):
    """Create a safe filename from paper title."""
    safe = "".join(c if c.isalnum() or c in (' ', '-', '_') else '' for c in title)
    safe = safe.strip()[:80]
    return f"paper_{paper_id:02d}_{safe}.pdf"

def get_unpaywall_url(doi):
    """Query Unpaywall API for OA PDF URL."""
    try:
        url = f"https://api.unpaywall.org/v2/{doi}?email={EMAIL}"
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = json.loads(resp.read().decode())
            if data.get("best_oa_location") and data["best_oa_location"].get("url_for_pdf"):
                return data["best_oa_location"]["url_for_pdf"]
            if data.get("best_oa_location") and data["best_oa_location"].get("url"):
                return data["best_oa_location"]["url"]
            # Check all OA locations
            for loc in data.get("oa_locations", []):
                if loc.get("url_for_pdf"):
                    return loc["url_for_pdf"]
            for loc in data.get("oa_locations", []):
                if loc.get("url"):
                    return loc["url"]
    except Exception as e:
        print(f"  Unpaywall error: {e}")
    return None

def get_semantic_scholar_url(doi):
    """Query Semantic Scholar API for open access PDF."""
    try:
        url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=openAccessPdf,isOpenAccess"
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = json.loads(resp.read().decode())
            if data.get("openAccessPdf") and data["openAccessPdf"].get("url"):
                return data["openAccessPdf"]["url"]
    except Exception as e:
        print(f"  Semantic Scholar error: {e}")
    return None

def get_direct_publisher_url(doi):
    """Try direct publisher PDF URLs for known OA publishers."""
    urls = []
    # MDPI
    if "10.3390/" in doi:
        article_id = doi.split("/")[-1]
        urls.append(f"https://www.mdpi.com/{doi.replace('10.3390/', '')}/pdf")
    # E3S Web of Conferences
    if "10.1051/e3sconf" in doi:
        urls.append(f"https://doi.org/{doi}")
    # IEEE Access (OA)
    if "10.1109/ACCESS" in doi:
        urls.append(f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?arnumber={doi.split('.')[-1]}")
    # Tech Science Press
    if "10.32604/" in doi:
        urls.append(f"https://doi.org/{doi}")
    return urls

def download_pdf(url, filepath):
    """Download a PDF from URL."""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/pdf,*/*"
        })
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            content_type = resp.headers.get('Content-Type', '')
            data = resp.read()
            # Check if it's actually a PDF
            if data[:5] == b'%PDF-' or 'pdf' in content_type.lower():
                with open(filepath, 'wb') as f:
                    f.write(data)
                size_mb = len(data) / (1024 * 1024)
                print(f"  ✅ Downloaded ({size_mb:.1f} MB): {os.path.basename(filepath)}")
                return True
            else:
                print(f"  ⚠️  Response is not PDF (Content-Type: {content_type})")
                return False
    except Exception as e:
        print(f"  ❌ Download failed: {e}")
        return False

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    oa_papers = [p for p in PAPERS if p["access"] == "OA"]
    pw_papers = [p for p in PAPERS if p["access"] == "PW"]
    
    print(f"{'='*60}")
    print(f"📚 Paper Download Script")
    print(f"{'='*60}")
    print(f"Total papers: {len(PAPERS)}")
    print(f"Open Access: {len(oa_papers)}")
    print(f"Paywall: {len(pw_papers)}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"{'='*60}\n")
    
    downloaded = []
    failed_oa = []
    skipped_pw = []
    
    # Try ALL papers (OA first, then PW - some PW might have OA versions)
    all_papers = oa_papers + pw_papers
    
    for i, paper in enumerate(all_papers):
        print(f"\n[{i+1}/{len(all_papers)}] Paper #{paper['id']}: {paper['title'][:60]}...")
        print(f"  DOI: {paper['doi']} | Access: {paper['access']}")
        
        filename = sanitize_filename(paper['title'], paper['id'])
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        if os.path.exists(filepath):
            print(f"  ⏭️  Already exists, skipping")
            downloaded.append(paper)
            continue
        
        # Strategy 1: Unpaywall API
        print("  🔍 Checking Unpaywall...")
        pdf_url = get_unpaywall_url(paper['doi'])
        
        if pdf_url:
            print(f"  📥 Found URL: {pdf_url[:80]}...")
            if download_pdf(pdf_url, filepath):
                downloaded.append(paper)
                time.sleep(1)
                continue
        
        time.sleep(0.5)
        
        # Strategy 2: Semantic Scholar
        print("  🔍 Checking Semantic Scholar...")
        pdf_url = get_semantic_scholar_url(paper['doi'])
        
        if pdf_url:
            print(f"  📥 Found URL: {pdf_url[:80]}...")
            if download_pdf(pdf_url, filepath):
                downloaded.append(paper)
                time.sleep(1)
                continue
        
        time.sleep(0.5)
        
        # Strategy 3: Direct publisher URLs
        direct_urls = get_direct_publisher_url(paper['doi'])
        for durl in direct_urls:
            print(f"  📥 Trying direct: {durl[:80]}...")
            if download_pdf(durl, filepath):
                downloaded.append(paper)
                break
        else:
            if paper['access'] == 'OA':
                failed_oa.append(paper)
            else:
                skipped_pw.append(paper)
            print(f"  ❌ Could not download")
        
        time.sleep(1)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 DOWNLOAD SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Downloaded: {len(downloaded)}")
    print(f"❌ Failed OA: {len(failed_oa)}")
    print(f"🔒 Paywall (no OA found): {len(skipped_pw)}")
    
    if downloaded:
        print(f"\n✅ Successfully downloaded papers:")
        for p in downloaded:
            print(f"  - #{p['id']}: {p['title'][:70]}")
    
    if failed_oa:
        print(f"\n❌ Failed OA papers (try manual download):")
        for p in failed_oa:
            print(f"  - #{p['id']}: https://doi.org/{p['doi']}")
    
    if skipped_pw:
        print(f"\n🔒 Paywall papers (need institutional access):")
        for p in skipped_pw:
            print(f"  - #{p['id']}: https://doi.org/{p['doi']}")
    
    # Save results to JSON
    results = {
        "downloaded": [{"id": p["id"], "doi": p["doi"], "title": p["title"]} for p in downloaded],
        "failed_oa": [{"id": p["id"], "doi": p["doi"], "title": p["title"]} for p in failed_oa],
        "paywall": [{"id": p["id"], "doi": p["doi"], "title": p["title"]} for p in skipped_pw],
    }
    with open(os.path.join(OUTPUT_DIR, "download_results.json"), 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n📄 Results saved to {OUTPUT_DIR}/download_results.json")

if __name__ == "__main__":
    main()
