// Populate the sidebar
//
// This is a script, and not included directly in the page, to control the total size of the book.
// The TOC contains an entry for each page, so if each page includes a copy of the TOC,
// the total size of the page becomes O(n**2).
class MDBookSidebarScrollbox extends HTMLElement {
    constructor() {
        super();
    }
    connectedCallback() {
        this.innerHTML = '<ol class="chapter"><li class="chapter-item expanded "><a href="index.html"><strong aria-hidden="true">1.</strong> Introduction to Aries Cloud API</a></li><li class="chapter-item expanded "><a href="Quick Start Guide.html"><strong aria-hidden="true">2.</strong> Quick Start Guide</a></li><li class="chapter-item expanded "><a href="Trust Registry.html"><strong aria-hidden="true">3.</strong> Trust Registry</a></li><li class="chapter-item expanded "><a href="NATS.html"><strong aria-hidden="true">4.</strong> NATS</a></li><li class="chapter-item expanded "><a href="Governance as Code.html"><strong aria-hidden="true">5.</strong> Governance as Code</a></li><li class="chapter-item expanded "><a href="Example Flows.html"><strong aria-hidden="true">6.</strong> Example Flows</a></li><li><ol class="section"><li class="chapter-item expanded "><a href="examples/1. Onboarding.html"><strong aria-hidden="true">6.1.</strong> Onboarding an Issuer, Verifier and a Holder</a></li><li class="chapter-item expanded "><a href="examples/2. Create Schema.html"><strong aria-hidden="true">6.2.</strong> Creating a Credential Schema</a></li><li class="chapter-item expanded "><a href="examples/3. Create Credential Definition.html"><strong aria-hidden="true">6.3.</strong> The Issuer creating a Credential definition</a></li><li class="chapter-item expanded "><a href="examples/4. Create Connection with Issuer.html"><strong aria-hidden="true">6.4.</strong> Create Connection between Issuer and Holder</a></li><li class="chapter-item expanded "><a href="examples/5. Issue Credential.html"><strong aria-hidden="true">6.5.</strong> Issuing a credential to a Holder</a></li><li class="chapter-item expanded "><a href="examples/6. Create Connection with Verifier.html"><strong aria-hidden="true">6.6.</strong> Create Connection between Verifier and Holder</a></li><li class="chapter-item expanded "><a href="examples/7. Verify Credential.html"><strong aria-hidden="true">6.7.</strong> The Verifier doing a proof request against the Holder&#39;s Credential</a></li><li class="chapter-item expanded "><a href="examples/8. Revoking Credentials.html"><strong aria-hidden="true">6.8.</strong> Revoking Credentials</a></li><li class="chapter-item expanded "><a href="examples/9. Verify Revoked Credentials.html"><strong aria-hidden="true">6.9.</strong> Verifying Revoked Credentials</a></li><li class="chapter-item expanded "><a href="examples/Self-Attested Attributes/1. Self-Attested Attributes.html"><strong aria-hidden="true">6.10.</strong> Self-Attested Attributes</a></li><li class="chapter-item expanded "><a href="examples/Restrictions on Proofs/1. Restrictions on Proofs.html"><strong aria-hidden="true">6.11.</strong> Restrictions on Proofs</a></li><li class="chapter-item expanded "><a href="examples/Requested Predicates/1. Requested Predicates.html"><strong aria-hidden="true">6.12.</strong> Requested Predicates</a></li></ol></li><li class="chapter-item expanded "><a href="Common Steps.html"><strong aria-hidden="true">7.</strong> Common Steps</a></li><li class="chapter-item expanded "><a href="Bootstrap Trust Ecosystem.html"><strong aria-hidden="true">8.</strong> Bootstrap Trust Ecosystem</a></li><li class="chapter-item expanded "><a href="Aries Cloud API Architecture.html"><strong aria-hidden="true">9.</strong> Aries Cloud API Architecture</a></li></ol>';
        // Set the current, active page, and reveal it if it's hidden
        let current_page = document.location.href.toString();
        if (current_page.endsWith("/")) {
            current_page += "index.html";
        }
        var links = Array.prototype.slice.call(this.querySelectorAll("a"));
        var l = links.length;
        for (var i = 0; i < l; ++i) {
            var link = links[i];
            var href = link.getAttribute("href");
            if (href && !href.startsWith("#") && !/^(?:[a-z+]+:)?\/\//.test(href)) {
                link.href = path_to_root + href;
            }
            // The "index" page is supposed to alias the first chapter in the book.
            if (link.href === current_page || (i === 0 && path_to_root === "" && current_page.endsWith("/index.html"))) {
                link.classList.add("active");
                var parent = link.parentElement;
                if (parent && parent.classList.contains("chapter-item")) {
                    parent.classList.add("expanded");
                }
                while (parent) {
                    if (parent.tagName === "LI" && parent.previousElementSibling) {
                        if (parent.previousElementSibling.classList.contains("chapter-item")) {
                            parent.previousElementSibling.classList.add("expanded");
                        }
                    }
                    parent = parent.parentElement;
                }
            }
        }
        // Track and set sidebar scroll position
        this.addEventListener('click', function(e) {
            if (e.target.tagName === 'A') {
                sessionStorage.setItem('sidebar-scroll', this.scrollTop);
            }
        }, { passive: true });
        var sidebarScrollTop = sessionStorage.getItem('sidebar-scroll');
        sessionStorage.removeItem('sidebar-scroll');
        if (sidebarScrollTop) {
            // preserve sidebar scroll position when navigating via links within sidebar
            this.scrollTop = sidebarScrollTop;
        } else {
            // scroll sidebar to current active section when navigating via "next/previous chapter" buttons
            var activeSection = document.querySelector('#sidebar .active');
            if (activeSection) {
                activeSection.scrollIntoView({ block: 'center' });
            }
        }
        // Toggle buttons
        var sidebarAnchorToggles = document.querySelectorAll('#sidebar a.toggle');
        function toggleSection(ev) {
            ev.currentTarget.parentElement.classList.toggle('expanded');
        }
        Array.from(sidebarAnchorToggles).forEach(function (el) {
            el.addEventListener('click', toggleSection);
        });
    }
}
window.customElements.define("mdbook-sidebar-scrollbox", MDBookSidebarScrollbox);
