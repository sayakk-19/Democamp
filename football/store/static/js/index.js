// let search = document.querySelector(".fa fa-user")

// search.addEventListener("click", ()=>{
//     search.innerHTML = '<input type="search" placeholder="Search here...">'
// })
console.log("====== SCRIPT START ======");

try {
    const rememberMe = document.querySelector(".remember-wrapper #remember");
    const inputsToRemember = document.querySelectorAll("input[type='text'], input[type='email'], input[type='password']");

    window.addEventListener("DOMContentLoaded", () => {
        if (localStorage.getItem("remembered") === "true") {
            rememberMe.checked = true;

            inputsToRemember.forEach(input => {
                let savedValue = localStorage.getItem("saved_" + input.name);
                if (savedValue) {
                    input.value = savedValue;
                }
            });
        }
    });

    let passtoggle = document.querySelector("#passwordToggle")
    console.log("Main Toggle Button Found:", passtoggle);
    let reenter_passtoggle = document.querySelector("#reenter_passwordToggle")


    // let i = 0
    // function eyeopenclose() {
    var pwrd = document.getElementById("password")
    passtoggle.addEventListener("click", (e) => {
        e.preventDefault()
        console.log("Main eye clicked");
        // let clickedButton = e.currentTarget;
        const eyeopened = this.querySelector(".eye-open")
        const eyeclosed = this.querySelector(".eye-closed")
        if (pwrd.type === "password") {
            pwrd.type = "text"
            eyeopened.style.visibility = "hidden"
            eyeclosed.style.visibility = "visible"
            eyeclosed.style.display = "flex"
            // eyeclosed.style.position = "absolute"
            // eyeclosed.style.justifyContent = "center"
            // eyeclosed.style.alignItems = "center"
            // i = 1;
        }

        else {
            pwrd.type = "password"
            eyeopened.style.visibility = "visible"
            eyeclosed.style.visibility = "hidden"
            // i = 0;
        }
    })

    console.log("Re-enter Toggle Button Found:", reenter_passtoggle);

    var reenter_password = document.getElementById("reenter_password")
    reenter_passtoggle.addEventListener("click", (e) => {
        e.preventDefault()
        console.log("Re-enter eye clicked");
        // let clickedButton = e.currentTarget;
        const eyeopen = reenter_passtoggle.querySelector(".eye-open")
        const eyeclose = reenter_passtoggle.querySelector(".eye-closed")
        if (reenter_password.type === "password") {
            reenter_password.type = "text"
            eyeopen.style.visibility = "hidden"
            eyeclose.style.visibility = "visible"
            eyeclose.style.display = "flex"
            // eyeclose.style.position = "absolute"
            // eyeclose.style.justifyContent = "center"
            // eyeclose.style.alignItems = "center"
        }

        else {
            reenter_password.type = "password"
            eyeopen.style.visibility = "visible"
            eyeclose.style.visibility = "hidden"
        }
    })
    // }

    // eyeopenclose()

    // let remember = document.querySelector(".remember-wrapper")
    // remember.addEventListener("click", () => {
    //     inputform.forEach((name, value) => {
    //         localStorage.setItem('input.name', 'input.value')
    //     });
    // })

    // let div = document.createElement('div')
    // let success_msg = div.innerHTML('<div class="success-message" id="successMessage"><divclass="success-icon neu-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12" /></svg></div><h3>Success!</h3><p>Redirecting to your dashboard...</p></div>')

    let submit = document.querySelector(".neu-button")
    console.log("Submit Button Found:", submit);
    let form_submit = document.querySelector('form')
    let span_repass_error = document.querySelector("#reenter_passwordError")

    submit.addEventListener("click", (e) => {
        console.log("Submit clicked");
        if (pwrd.value != reenter_password.value) {
            e.preventDefault()
            span_repass_error.textContent = "Mismatch in passwords please provide same password..."
            // setTimeout(()=>{window.location.href = "../../store/registration.html"
            // }, 1500)

        }
        else {
            e.preventDefault()

            if (rememberMe.checked) {
                localStorage.setItem("remembered", "true")
                inputsToRemember.forEach(input => {
                    localStorage.setItem("saved_" + input.name, input.value)
                })
            }
            else {
                localStorage.removeItem("remembered")
                inputsToRemember.forEach(input => {
                    localStorage.removeItem("saved_" + input.name)
                })
            }
            // document.querySelector(".login-card").appendChild('success_msg')
            console.log("Passwords match, forcing Django submit...")
            window.location.href = "../../store/index1.html"
            form_submit.submit()
        }
    })


    console.log("====== SCRIPT LOADED SUCCESSFULLY ======");

    // let success_page = document.querySelector(".social-login")


} catch (error) {
    console.error("CRITICAL SCRIPT CRASH:", error);
}