// AWS Configuration for Amplify
export const awsConfig = {
  API: {
    endpoints: [
      {
        name: "TaxDocAPI",
        endpoint: "https://n82datyqse.execute-api.us-east-1.amazonaws.com/prod",
        region: "us-east-1"
      }
    ]
  }
};